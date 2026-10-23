from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.engine import (
    LoadPlanResult,
    calculate_volume_load_plan,
)
from app.modules.load_planning.optimizer.ordering import order_volumes
from app.modules.load_planning.optimizer.volumes import validate_individual_volumes

MAX_DISTRIBUTION_TRUCKS = 10
MAX_SEARCH_STATES = 64


class InvalidMultiTruckOptimizationInputError(ValueError):
    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


@dataclass(frozen=True, slots=True)
class MultiTruckCandidate:
    truck_id: UUID
    capacity: TruckCapacityInput

    def __post_init__(self) -> None:
        if not isinstance(self.truck_id, UUID):
            raise InvalidMultiTruckOptimizationInputError("truck_id", "must be a UUID")
        if not isinstance(self.capacity, TruckCapacityInput):
            raise InvalidMultiTruckOptimizationInputError(
                "capacity", "must be a TruckCapacityInput"
            )

    @property
    def internal_volume_cm3(self) -> int:
        return (
            self.capacity.internal_width_cm
            * self.capacity.internal_height_cm
            * self.capacity.internal_length_cm
        )


@dataclass(frozen=True, slots=True)
class MultiTruckPart:
    truck_id: UUID
    volumes: tuple[IndividualVolume, ...]
    load_plan: LoadPlanResult


@dataclass(frozen=True, slots=True)
class MultiTruckFailure:
    identity: VolumeIdentity
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MultiTruckOptimizationResult:
    parts: tuple[MultiTruckPart, ...]
    remaining_volumes: tuple[IndividualVolume, ...]
    failures: tuple[MultiTruckFailure, ...]
    attempt_count: int

    @property
    def complete(self) -> bool:
        return not self.remaining_volumes


@dataclass(frozen=True, slots=True)
class _SearchState:
    parts: tuple[MultiTruckPart, ...]
    remaining_volumes: tuple[IndividualVolume, ...]


def _identity_key(volume: IndividualVolume) -> tuple[int, int]:
    return (volume.order_item_id.int, volume.volume_index)


def _candidate_key(
    candidate: MultiTruckCandidate,
) -> tuple[int, Decimal, int, int, int, int]:
    return (
        candidate.internal_volume_cm3,
        candidate.capacity.max_weight_kg,
        candidate.capacity.internal_width_cm,
        candidate.capacity.internal_height_cm,
        candidate.capacity.internal_length_cm,
        candidate.truck_id.int,
    )


def _assignment_key(
    state: _SearchState,
) -> tuple[tuple[int, tuple[tuple[int, int], ...]], ...]:
    return tuple(
        sorted(
            (
                part.truck_id.int,
                tuple(_identity_key(volume) for volume in part.volumes),
            )
            for part in state.parts
        )
    )


def _fleet_capacity_key(
    state: _SearchState,
    candidates_by_id: dict[UUID, MultiTruckCandidate],
) -> tuple[int, Decimal]:
    selected = tuple(candidates_by_id[part.truck_id] for part in state.parts)
    return (
        sum(candidate.internal_volume_cm3 for candidate in selected),
        sum(
            (candidate.capacity.max_weight_kg for candidate in selected),
            start=Decimal(0),
        ),
    )


def _solution_key(
    state: _SearchState,
    candidates_by_id: dict[UUID, MultiTruckCandidate],
) -> tuple[
    int,
    Decimal,
    tuple[int, ...],
    tuple[tuple[int, tuple[tuple[int, int], ...]], ...],
]:
    total_volume, total_weight = _fleet_capacity_key(state, candidates_by_id)
    return (
        total_volume,
        total_weight,
        tuple(sorted(part.truck_id.int for part in state.parts)),
        _assignment_key(state),
    )


def _partial_key(
    state: _SearchState,
    candidates_by_id: dict[UUID, MultiTruckCandidate],
) -> tuple[
    int,
    int,
    Decimal,
    int,
    Decimal,
    tuple[int, ...],
    tuple[tuple[int, tuple[tuple[int, int], ...]], ...],
]:
    total_capacity, total_max_weight = _fleet_capacity_key(state, candidates_by_id)
    return (
        len(state.remaining_volumes),
        sum(volume.volume_cm3 for volume in state.remaining_volumes),
        sum(
            (volume.weight_kg for volume in state.remaining_volumes),
            start=Decimal(0),
        ),
        total_capacity,
        total_max_weight,
        tuple(sorted(part.truck_id.int for part in state.parts)),
        _assignment_key(state),
    )


def _dedupe_key(
    state: _SearchState,
) -> tuple[tuple[tuple[int, int], ...], tuple[int, ...]]:
    return (
        tuple(_identity_key(volume) for volume in state.remaining_volumes),
        tuple(sorted(part.truck_id.int for part in state.parts)),
    )


def _validate_candidates(
    candidates: Sequence[MultiTruckCandidate],
) -> tuple[MultiTruckCandidate, ...]:
    if not isinstance(candidates, Sequence) or isinstance(
        candidates, (str, bytes, bytearray)
    ):
        raise InvalidMultiTruckOptimizationInputError(
            "candidates", "must be an ordered sequence of MultiTruckCandidate"
        )

    prepared = tuple(candidates)
    for position, candidate in enumerate(prepared):
        if not isinstance(candidate, MultiTruckCandidate):
            raise InvalidMultiTruckOptimizationInputError(
                f"candidates[{position}]",
                "must be a MultiTruckCandidate",
            )

    identifiers = tuple(candidate.truck_id for candidate in prepared)
    if len(set(identifiers)) != len(identifiers):
        raise InvalidMultiTruckOptimizationInputError(
            "candidates", "must not contain duplicate truck ids"
        )

    return tuple(sorted(prepared, key=_candidate_key))


def _validate_volumes(
    volumes: Sequence[IndividualVolume],
) -> tuple[IndividualVolume, ...]:
    if not isinstance(volumes, Sequence) or isinstance(
        volumes, (str, bytes, bytearray)
    ):
        raise InvalidMultiTruckOptimizationInputError(
            "volumes", "must be an ordered sequence of IndividualVolume"
        )

    prepared = tuple(volumes)
    if not prepared:
        raise InvalidMultiTruckOptimizationInputError("volumes", "must not be empty")

    validate_individual_volumes(prepared)
    return order_volumes(prepared)


def optimize_multi_truck(
    candidates: Sequence[MultiTruckCandidate],
    volumes: Sequence[IndividualVolume],
) -> MultiTruckOptimizationResult:
    """Find a deterministic complete partition using the existing physical engine."""

    ordered_candidates = _validate_candidates(candidates)
    ordered_volumes = _validate_volumes(volumes)

    if not ordered_candidates:
        return MultiTruckOptimizationResult(
            parts=(),
            remaining_volumes=tuple(sorted(ordered_volumes, key=_identity_key)),
            failures=(),
            attempt_count=0,
        )

    candidates_by_id = {
        candidate.truck_id: candidate for candidate in ordered_candidates
    }
    failures_by_identity: dict[VolumeIdentity, set[str]] = {}
    cache: dict[
        tuple[TruckCapacityInput, tuple[tuple[int, int], ...]],
        LoadPlanResult,
    ] = {}
    attempt_count = 0

    def calculate(
        candidate: MultiTruckCandidate,
        remaining: tuple[IndividualVolume, ...],
    ) -> LoadPlanResult:
        nonlocal attempt_count

        # Physical packing depends on capacity and volume identities, not truck UUID.
        key = (
            candidate.capacity,
            tuple(_identity_key(volume) for volume in remaining),
        )
        cached = cache.get(key)
        if cached is not None:
            return cached

        result = calculate_volume_load_plan(candidate.capacity, remaining)
        cache[key] = result
        attempt_count += 1

        for rejected in result.rejected_volumes:
            failures_by_identity.setdefault(rejected.volume.identity, set()).add(
                rejected.rejection_reason.value
            )

        return result

    initial = _SearchState(
        parts=(),
        remaining_volumes=tuple(sorted(ordered_volumes, key=_identity_key)),
    )
    frontier = (initial,)
    best_state = initial

    max_depth = min(
        MAX_DISTRIBUTION_TRUCKS,
        len(ordered_candidates),
        len(ordered_volumes),
    )

    for _depth in range(1, max_depth + 1):
        complete_states: list[_SearchState] = []
        partial_states: list[_SearchState] = []

        for state in frontier:
            used_trucks = {part.truck_id for part in state.parts}

            for candidate in ordered_candidates:
                if candidate.truck_id in used_trucks:
                    continue

                result = calculate(candidate, state.remaining_volumes)
                placed = tuple(
                    sorted(
                        (item.volume for item in result.placed_volumes),
                        key=_identity_key,
                    )
                )

                if not placed:
                    continue

                remaining = tuple(
                    sorted(
                        (item.volume for item in result.rejected_volumes),
                        key=_identity_key,
                    )
                )
                next_state = _SearchState(
                    parts=(
                        *state.parts,
                        MultiTruckPart(
                            truck_id=candidate.truck_id,
                            volumes=placed,
                            load_plan=result,
                        ),
                    ),
                    remaining_volumes=remaining,
                )

                if _partial_key(next_state, candidates_by_id) < _partial_key(
                    best_state, candidates_by_id
                ):
                    best_state = next_state

                if not remaining:
                    complete_states.append(next_state)
                else:
                    partial_states.append(next_state)

        if complete_states:
            winner = min(
                complete_states,
                key=lambda state: _solution_key(state, candidates_by_id),
            )
            return MultiTruckOptimizationResult(
                parts=winner.parts,
                remaining_volumes=(),
                failures=(),
                attempt_count=attempt_count,
            )

        if not partial_states:
            break

        deduplicated: dict[
            tuple[tuple[tuple[int, int], ...], tuple[int, ...]],
            _SearchState,
        ] = {}

        for state in sorted(
            partial_states,
            key=lambda item: _partial_key(item, candidates_by_id),
        ):
            key = _dedupe_key(state)
            current = deduplicated.get(key)
            if current is None or _partial_key(state, candidates_by_id) < _partial_key(
                current, candidates_by_id
            ):
                deduplicated[key] = state

        frontier = tuple(
            sorted(
                deduplicated.values(),
                key=lambda state: _partial_key(state, candidates_by_id),
            )[:MAX_SEARCH_STATES]
        )

    remaining = tuple(sorted(best_state.remaining_volumes, key=_identity_key))
    failures = tuple(
        MultiTruckFailure(
            identity=volume.identity,
            reasons=tuple(sorted(failures_by_identity.get(volume.identity, set()))),
        )
        for volume in remaining
    )

    return MultiTruckOptimizationResult(
        parts=best_state.parts,
        remaining_volumes=remaining,
        failures=failures,
        attempt_count=attempt_count,
    )
