from collections.abc import Sequence
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import combinations
from uuid import UUID

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.geometry import (
    InternalDimensions,
    PositionedAABB,
    fits_within_bounds,
)
from app.modules.load_planning.optimizer.placement import PlacementCandidate
from app.modules.load_planning.optimizer.rotations import RotationCode, RotationOption
from app.modules.load_planning.optimizer.support import (
    analyze_support_configuration,
    is_support_configuration_valid,
)


class LoadingSequenceDomainError(ValueError):
    code: str


class InvalidLoadingSequenceInputError(LoadingSequenceDomainError):
    code = "INVALID_LOADING_SEQUENCE_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class LoadingSequenceInvariantError(RuntimeError):
    code = "LOADING_SEQUENCE_INVARIANT_VIOLATION"


@dataclass(frozen=True)
class SequencedPlacement:
    """A placement that passed the integrated engine and received a load order."""

    placement: PlacementCandidate
    loading_sequence: int

    def __post_init__(self) -> None:
        if not isinstance(self.placement, PlacementCandidate):
            raise InvalidLoadingSequenceInputError(
                "placement", "must be a PlacementCandidate"
            )
        if (
            not isinstance(self.loading_sequence, int)
            or isinstance(self.loading_sequence, bool)
            or self.loading_sequence <= 0
        ):
            raise InvalidLoadingSequenceInputError(
                "loading_sequence", "must be a positive integer"
            )

    @property
    def identity(self) -> VolumeIdentity:
        return self.placement.identity

    @property
    def volume(self) -> IndividualVolume:
        return self.placement.volume

    @property
    def rotation(self) -> RotationOption:
        return self.placement.rotation

    @property
    def box(self) -> PositionedAABB:
        return self.placement.box

    @property
    def rotation_code(self) -> RotationCode:
        return self.placement.rotation_code

    @property
    def position_x_cm(self) -> int:
        return self.placement.position_x_cm

    @property
    def position_y_cm(self) -> int:
        return self.placement.position_y_cm

    @property
    def position_z_cm(self) -> int:
        return self.placement.position_z_cm

    @property
    def used_width_cm(self) -> int:
        return self.placement.used_width_cm

    @property
    def used_height_cm(self) -> int:
        return self.placement.used_height_cm

    @property
    def used_length_cm(self) -> int:
        return self.placement.used_length_cm


def _validate_identity(identity: object, field_name: str) -> VolumeIdentity:
    if not isinstance(identity, VolumeIdentity):
        raise InvalidLoadingSequenceInputError(
            field_name, "must be a VolumeIdentity"
        )
    if not isinstance(identity.order_item_id, UUID):
        raise InvalidLoadingSequenceInputError(
            f"{field_name}.order_item_id", "must be a UUID"
        )
    if (
        not isinstance(identity.volume_index, int)
        or isinstance(identity.volume_index, bool)
        or identity.volume_index <= 0
    ):
        raise InvalidLoadingSequenceInputError(
            f"{field_name}.volume_index", "must be a positive integer"
        )
    return identity


def _validate_placements(
    placements: Sequence[PlacementCandidate],
    bounds: InternalDimensions,
    field_name: str,
) -> tuple[PlacementCandidate, ...]:
    if not isinstance(bounds, InternalDimensions):
        raise InvalidLoadingSequenceInputError(
            "bounds", "must be InternalDimensions"
        )
    if not isinstance(placements, Sequence) or isinstance(
        placements, (str, bytes, bytearray)
    ):
        raise InvalidLoadingSequenceInputError(
            field_name, "must be an ordered sequence of PlacementCandidate"
        )

    validated = tuple(placements)
    seen_identities: set[VolumeIdentity] = set()
    for position, placement in enumerate(validated):
        prefix = f"{field_name}[{position}]"
        if not isinstance(placement, PlacementCandidate):
            raise InvalidLoadingSequenceInputError(
                prefix, "must be a PlacementCandidate"
            )
        identity = _validate_identity(placement.identity, f"{prefix}.identity")
        if identity in seen_identities:
            raise InvalidLoadingSequenceInputError(
                field_name, "must contain unique volume identities"
            )
        seen_identities.add(identity)
        delivery_sequence = placement.volume.delivery_sequence
        if (
            not isinstance(delivery_sequence, int)
            or isinstance(delivery_sequence, bool)
            or delivery_sequence <= 0
        ):
            raise InvalidLoadingSequenceInputError(
                f"{prefix}.volume.delivery_sequence",
                "must be a positive integer",
            )
        if not fits_within_bounds(placement.box, bounds):
            raise InvalidLoadingSequenceInputError(
                f"{prefix}.box", "must fit within bounds"
            )
    return validated


def _identity_key(identity: VolumeIdentity) -> tuple[int, int]:
    return (identity.order_item_id.int, identity.volume_index)


def _door_distance_cm(
    placement: PlacementCandidate,
    bounds: InternalDimensions,
) -> int:
    return bounds.internal_length_cm - (
        placement.position_z_cm + placement.used_length_cm
    )


def calculate_door_distance_cm(
    placement: PlacementCandidate,
    bounds: InternalDimensions,
) -> int:
    """Return clearance from the placement's door-facing face to the door at z=L."""

    validated = _validate_placements((placement,), bounds, "placements")
    return _door_distance_cm(validated[0], bounds)


def is_delivery_depth_configuration_valid(
    placements: Sequence[PlacementCandidate],
    bounds: InternalDimensions,
) -> bool:
    """Require later deliveries to be at least as deep as earlier deliveries."""

    validated = _validate_placements(placements, bounds, "placements")
    for first, second in combinations(validated, 2):
        if first.volume.delivery_sequence == second.volume.delivery_sequence:
            continue

        later, earlier = (
            (first, second)
            if first.volume.delivery_sequence > second.volume.delivery_sequence
            else (second, first)
        )
        if _door_distance_cm(later, bounds) < _door_distance_cm(earlier, bounds):
            return False
    return True


def is_candidate_delivery_depth_valid(
    candidate: PlacementCandidate,
    placed_candidates: Sequence[PlacementCandidate],
    bounds: InternalDimensions,
) -> bool:
    if not isinstance(candidate, PlacementCandidate):
        raise InvalidLoadingSequenceInputError(
            "candidate", "must be a PlacementCandidate"
        )
    if not isinstance(placed_candidates, Sequence) or isinstance(
        placed_candidates, (str, bytes, bytearray)
    ):
        raise InvalidLoadingSequenceInputError(
            "placed_candidates",
            "must be an ordered sequence of PlacementCandidate",
        )
    return is_delivery_depth_configuration_valid(
        (*tuple(placed_candidates), candidate),
        bounds,
    )


def assign_loading_sequences(
    placements: Sequence[PlacementCandidate],
    bounds: InternalDimensions,
) -> tuple[SequencedPlacement, ...]:
    """Topologically order supports before supported volumes with D12 tie-breaks."""

    validated = _validate_placements(placements, bounds, "placements")
    if not is_support_configuration_valid(validated):
        raise InvalidLoadingSequenceInputError(
            "placements", "must form a valid support configuration"
        )
    if not is_delivery_depth_configuration_valid(validated, bounds):
        raise InvalidLoadingSequenceInputError(
            "placements", "must follow delivery depth monotonicity"
        )

    placements_by_identity = {
        placement.identity: placement for placement in validated
    }
    assessments = analyze_support_configuration(validated)
    in_degree = {
        assessment.identity: len(assessment.direct_supporter_identities)
        for assessment in assessments
    }
    dependents: dict[VolumeIdentity, list[VolumeIdentity]] = {
        identity: [] for identity in placements_by_identity
    }
    for assessment in assessments:
        for supporter_identity in assessment.direct_supporter_identities:
            dependents[supporter_identity].append(assessment.identity)

    ready: list[tuple[int, int, int, int]] = []

    def push_ready(identity: VolumeIdentity) -> None:
        placement = placements_by_identity[identity]
        heappush(
            ready,
            (
                -placement.volume.delivery_sequence,
                -_door_distance_cm(placement, bounds),
                *_identity_key(identity),
            ),
        )

    for identity, degree in in_degree.items():
        if degree == 0:
            push_ready(identity)

    ordered_identities: list[VolumeIdentity] = []
    while ready:
        _delivery_rank, _distance_rank, order_item_rank, volume_index = heappop(
            ready
        )
        identity = VolumeIdentity(UUID(int=order_item_rank), volume_index)
        ordered_identities.append(identity)

        for dependent_identity in sorted(
            dependents[identity], key=_identity_key
        ):
            in_degree[dependent_identity] -= 1
            if in_degree[dependent_identity] == 0:
                push_ready(dependent_identity)

    if len(ordered_identities) != len(validated):
        raise LoadingSequenceInvariantError(
            "support dependency graph must be acyclic"
        )

    return tuple(
        SequencedPlacement(
            placement=placements_by_identity[identity],
            loading_sequence=sequence,
        )
        for sequence, identity in enumerate(ordered_identities, start=1)
    )
