from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from functools import partial

from app.modules.load_planning.optimizer.capacity import (
    TruckCapacityInput,
    TruckCapacityResult,
    calculate_truck_capacity,
)
from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    OrderItemInput,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.geometry import (
    InternalDimensions,
    PositionedAABB,
    fits_within_bounds,
    is_collision_free,
)
from app.modules.load_planning.optimizer.loading_sequence import (
    LoadingSequenceDomainError,
    SequencedPlacement,
    assign_loading_sequences,
    is_candidate_delivery_depth_valid,
    is_delivery_depth_configuration_valid,
)
from app.modules.load_planning.optimizer.metrics import (
    LoadMetrics,
    calculate_load_metrics,
)
from app.modules.load_planning.optimizer.ordering import order_volumes
from app.modules.load_planning.optimizer.placement import (
    NoValidPositionError,
    PlacementCandidate,
    TruckDimensionsExceededError,
    select_first_valid_candidate,
)
from app.modules.load_planning.optimizer.rejections import (
    REJECTION_REASON_PRECEDENCE,
    RejectionReason,
    select_rejection_reason,
)
from app.modules.load_planning.optimizer.rotations import generate_rotations
from app.modules.load_planning.optimizer.support import (
    analyze_support_configuration,
    is_candidate_support_valid,
    is_support_configuration_valid,
)
from app.modules.load_planning.optimizer.volumes import expand_order_items
from app.modules.load_planning.optimizer.weight import (
    WeightLimitExceededError,
    calculate_next_weight,
)

MAX_VOLUMES = 200


class EngineDomainError(ValueError):
    code: str


class InvalidEngineInputError(EngineDomainError):
    code = "INVALID_ENGINE_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class LoadPlanVolumeLimitExceededError(EngineDomainError):
    code = "LOAD_PLAN_VOLUME_LIMIT_EXCEEDED"

    def __init__(self, volume_count: int, max_volumes: int = MAX_VOLUMES) -> None:
        self.volume_count = volume_count
        self.max_volumes = max_volumes
        super().__init__(
            f"expanded load contains {volume_count} volumes; maximum is {max_volumes}"
        )


class EngineInvariantError(RuntimeError):
    code = "LOAD_PLAN_INVARIANT_VIOLATION"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


@dataclass(frozen=True)
class RejectedVolume:
    volume: IndividualVolume
    rejection_reason: RejectionReason

    def __post_init__(self) -> None:
        if not isinstance(self.volume, IndividualVolume):
            raise InvalidEngineInputError(
                "volume", "must be an IndividualVolume"
            )
        if not isinstance(self.rejection_reason, RejectionReason):
            raise InvalidEngineInputError(
                "rejection_reason", "must be a RejectionReason"
            )

    @property
    def identity(self) -> VolumeIdentity:
        return self.volume.identity


@dataclass(frozen=True)
class LoadPlanResult:
    capacity: TruckCapacityResult
    placed_volumes: tuple[SequencedPlacement, ...]
    rejected_volumes: tuple[RejectedVolume, ...]
    metrics: LoadMetrics


@dataclass
class _CandidateSearchFrontier:
    saw_candidate: bool = False
    saw_collision_free: bool = False
    saw_support_valid: bool = False
    support_reasons: set[RejectionReason] = field(default_factory=set)

    def rejection_reason(self) -> RejectionReason:
        if self.saw_support_valid or not self.saw_candidate:
            return RejectionReason.NO_VALID_POSITION
        if self.saw_collision_free:
            ordered_reasons = tuple(
                reason
                for reason in REJECTION_REASON_PRECEDENCE
                if reason in self.support_reasons
            )
            if not ordered_reasons:
                raise EngineInvariantError(
                    "candidate_frontier",
                    "support rejection must have a structural reason",
                )
            return select_rejection_reason(ordered_reasons)
        return RejectionReason.COLLISION


def _has_dimensionally_viable_rotation(
    volume: IndividualVolume,
    bounds: InternalDimensions,
) -> bool:
    return any(
        rotation.used_width_cm <= bounds.internal_width_cm
        and rotation.used_height_cm <= bounds.internal_height_cm
        and rotation.used_length_cm <= bounds.internal_length_cm
        for rotation in generate_rotations(volume)
    )


def _preflight_volume_count(order_items: object) -> None:
    if not isinstance(order_items, Sequence) or isinstance(
        order_items, (str, bytes, bytearray)
    ):
        raise InvalidEngineInputError(
            "order_items", "must be an ordered sequence of OrderItemInput"
        )
    if not order_items:
        raise InvalidEngineInputError("order_items", "must not be empty")

    volume_count = 0
    for position, item in enumerate(order_items):
        if not isinstance(item, OrderItemInput):
            raise InvalidEngineInputError(
                f"order_items[{position}]", "must be an OrderItemInput"
            )
        if (
            not isinstance(item.quantity, int)
            or isinstance(item.quantity, bool)
            or item.quantity <= 0
        ):
            raise InvalidEngineInputError(
                f"order_items[{position}].quantity",
                "must be a positive integer",
            )
        volume_count += item.quantity
        if volume_count > MAX_VOLUMES:
            raise LoadPlanVolumeLimitExceededError(volume_count)


def _weight_context(*weights: Decimal) -> Context:
    minimum_exponent = min(weight.as_tuple().exponent for weight in weights)
    highest_adjusted = max(weight.adjusted() for weight in weights)
    required_precision = (
        highest_adjusted - minimum_exponent + len(str(MAX_VOLUMES)) + 2
    )
    return Context(prec=max(28, required_precision), rounding=ROUND_HALF_UP)


def _calculate_next_weight_deterministically(
    current_weight_kg: Decimal,
    candidate_weight_kg: Decimal,
    max_weight_kg: Decimal,
) -> Decimal:
    with localcontext(
        _weight_context(
            current_weight_kg,
            candidate_weight_kg,
            max_weight_kg,
        )
    ):
        return calculate_next_weight(
            current_weight_kg,
            candidate_weight_kg,
            max_weight_kg,
        )


def _support_rejection_reasons(
    candidate: PlacementCandidate,
    placed_candidates: tuple[PlacementCandidate, ...],
) -> tuple[RejectionReason, ...]:
    if is_candidate_support_valid(candidate, placed_candidates):
        return ()

    configuration = (*placed_candidates, candidate)
    placements_by_identity = {
        placement.identity: placement for placement in configuration
    }
    detected: set[RejectionReason] = set()
    for assessment in analyze_support_configuration(configuration):
        if any(
            not placements_by_identity[identity].volume.stackable
            for identity in assessment.direct_supporter_identities
        ):
            detected.add(RejectionReason.NON_STACKABLE_SUPPORT)
        if any(
            placements_by_identity[identity].volume.fragile
            for identity in assessment.load_bearing_supporter_identities
        ):
            detected.add(RejectionReason.FRAGILE_SUPPORT_WEIGHT_EXCEEDED)
        if not assessment.is_fully_supported:
            detected.add(RejectionReason.INSUFFICIENT_SUPPORT)

    reasons = tuple(
        reason for reason in REJECTION_REASON_PRECEDENCE if reason in detected
    )
    if not reasons:
        raise EngineInvariantError(
            "support_configuration",
            "invalid support configuration must have a structural reason",
        )
    return reasons


def _make_rejection(
    volume: IndividualVolume,
    reason: RejectionReason,
) -> RejectedVolume:
    return RejectedVolume(volume=volume, rejection_reason=reason)


def _validate_candidate_for_engine(
    candidate: PlacementCandidate,
    *,
    frontier: _CandidateSearchFrontier,
    placed_candidates: tuple[PlacementCandidate, ...],
    placed_boxes: tuple[PositionedAABB, ...],
    bounds: InternalDimensions,
) -> bool:
    frontier.saw_candidate = True
    if not is_collision_free(candidate.box, placed_boxes):
        return False
    frontier.saw_collision_free = True

    support_reasons = _support_rejection_reasons(candidate, placed_candidates)
    if support_reasons:
        frontier.support_reasons.update(support_reasons)
        return False
    frontier.saw_support_valid = True
    return is_candidate_delivery_depth_valid(
        candidate,
        placed_candidates,
        bounds,
    )


def _require_invariant(condition: bool, field_name: str, reason: str) -> None:
    if not condition:
        raise EngineInvariantError(field_name, reason)


def _revalidate_final_result(
    result: LoadPlanResult,
    expanded_volumes: tuple[IndividualVolume, ...],
    bounds: InternalDimensions,
    accepted_weight_kg: Decimal,
) -> None:
    placements = tuple(item.placement for item in result.placed_volumes)
    placed_volumes = tuple(item.volume for item in result.placed_volumes)
    rejected_volumes = tuple(item.volume for item in result.rejected_volumes)

    source_by_identity = {volume.identity: volume for volume in expanded_volumes}
    output_volumes = (*placed_volumes, *rejected_volumes)
    output_identities = tuple(volume.identity for volume in output_volumes)
    _require_invariant(
        len(output_identities) == len(set(output_identities)),
        "volumes",
        "must contain unique identities",
    )
    _require_invariant(
        set(output_identities) == set(source_by_identity),
        "volumes",
        "must be a complete partition of expanded input",
    )
    _require_invariant(
        all(volume == source_by_identity[volume.identity] for volume in output_volumes),
        "volumes",
        "must preserve every expanded input volume",
    )

    for position, placement in enumerate(placements):
        _require_invariant(
            fits_within_bounds(placement.box, bounds),
            f"placed_volumes[{position}].box",
            "must fit within bounds",
        )
        _require_invariant(
            placement.rotation in generate_rotations(placement.volume),
            f"placed_volumes[{position}].rotation",
            "must be allowed for the volume",
        )
        _require_invariant(
            is_collision_free(
                placement.box,
                tuple(other.box for other in placements[position + 1 :]),
            ),
            f"placed_volumes[{position}].box",
            "must be collision free",
        )

    _require_invariant(
        is_support_configuration_valid(placements),
        "placed_volumes",
        "must form a valid support configuration",
    )
    _require_invariant(
        is_delivery_depth_configuration_valid(placements, bounds),
        "placed_volumes",
        "must follow delivery depth monotonicity",
    )
    _require_invariant(
        assign_loading_sequences(placements, bounds) == result.placed_volumes,
        "placed_volumes",
        "must use the deterministic loading sequence",
    )

    revalidated_weight = Decimal(0)
    for volume in placed_volumes:
        revalidated_weight = _calculate_next_weight_deterministically(
            revalidated_weight,
            volume.weight_kg,
            result.capacity.max_weight_kg,
        )
    _require_invariant(
        revalidated_weight == accepted_weight_kg,
        "metrics.total_weight_kg",
        "must match accepted incremental weight",
    )

    expected_metrics = calculate_load_metrics(
        internal_volume_cm3=result.capacity.internal_volume_cm3,
        placed_volumes=placed_volumes,
        rejected_volumes=rejected_volumes,
    )
    _require_invariant(
        result.metrics == expected_metrics,
        "metrics",
        "must match a fresh deterministic calculation",
    )
    _require_invariant(
        result.metrics.total_weight_kg == accepted_weight_kg,
        "metrics.total_weight_kg",
        "must match accepted incremental weight",
    )
    _require_invariant(
        all(
            isinstance(item.rejection_reason, RejectionReason)
            for item in result.rejected_volumes
        ),
        "rejected_volumes",
        "must use only catalog rejection reasons",
    )


def calculate_load_plan(
    truck: TruckCapacityInput,
    order_items: Sequence[OrderItemInput],
) -> LoadPlanResult:
    """Run the complete deterministic heuristic without database or HTTP access."""

    if not isinstance(truck, TruckCapacityInput):
        raise InvalidEngineInputError("truck", "must be a TruckCapacityInput")

    capacity = calculate_truck_capacity(truck)
    _preflight_volume_count(order_items)
    expanded_volumes = expand_order_items(order_items)

    ordering_weights = tuple(volume.weight_kg for volume in expanded_volumes)
    with localcontext(
        _weight_context(*(ordering_weights + (capacity.max_weight_kg,)))
    ):
        ordered_volumes = order_volumes(expanded_volumes)
    bounds = InternalDimensions(
        capacity.internal_width_cm,
        capacity.internal_height_cm,
        capacity.internal_length_cm,
    )
    placed_candidates: list[PlacementCandidate] = []
    rejected_volumes: list[RejectedVolume] = []
    current_weight_kg = Decimal(0)

    for volume in ordered_volumes:
        if not _has_dimensionally_viable_rotation(volume, bounds):
            rejected_volumes.append(
                _make_rejection(
                    volume,
                    RejectionReason.TRUCK_DIMENSIONS_EXCEEDED,
                )
            )
            continue

        try:
            next_weight_kg = _calculate_next_weight_deterministically(
                current_weight_kg,
                volume.weight_kg,
                capacity.max_weight_kg,
            )
        except WeightLimitExceededError:
            rejected_volumes.append(
                _make_rejection(volume, RejectionReason.TRUCK_WEIGHT_EXCEEDED)
            )
            continue

        placed_snapshot = tuple(placed_candidates)
        placed_boxes = tuple(placement.box for placement in placed_snapshot)
        frontier = _CandidateSearchFrontier()
        validate_candidate = partial(
            _validate_candidate_for_engine,
            frontier=frontier,
            placed_candidates=placed_snapshot,
            placed_boxes=placed_boxes,
            bounds=bounds,
        )

        try:
            candidate = select_first_valid_candidate(
                volume,
                bounds,
                placed_boxes,
                validate_candidate=validate_candidate,
            )
        except TruckDimensionsExceededError:
            rejected_volumes.append(
                _make_rejection(
                    volume,
                    RejectionReason.TRUCK_DIMENSIONS_EXCEEDED,
                )
            )
        except NoValidPositionError:
            rejected_volumes.append(
                _make_rejection(volume, frontier.rejection_reason())
            )
        else:
            placed_candidates.append(candidate)
            current_weight_kg = next_weight_kg

    try:
        sequenced_placements = assign_loading_sequences(
            tuple(placed_candidates),
            bounds,
        )
    except LoadingSequenceDomainError as exc:
        raise EngineInvariantError(
            "placed_volumes", "failed final loading sequence validation"
        ) from exc

    rejected = tuple(rejected_volumes)
    metrics = calculate_load_metrics(
        internal_volume_cm3=capacity.internal_volume_cm3,
        placed_volumes=tuple(item.volume for item in sequenced_placements),
        rejected_volumes=tuple(item.volume for item in rejected),
    )
    result = LoadPlanResult(
        capacity=capacity,
        placed_volumes=sequenced_placements,
        rejected_volumes=rejected,
        metrics=metrics,
    )
    _revalidate_final_result(
        result,
        expanded_volumes,
        bounds,
        current_weight_kg,
    )
    return result
