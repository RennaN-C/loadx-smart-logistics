from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import OrderItemInput
from app.modules.load_planning.optimizer.engine import (
    MAX_VOLUMES,
    LoadPlanResult,
    LoadPlanVolumeLimitExceededError,
    calculate_load_plan,
)
from app.modules.load_planning.optimizer.volumes import expand_order_items

MAX_COMPARISON_TRUCKS = 10


class InvalidTruckComparisonInputError(ValueError):
    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class TruckComparisonLimitExceededError(ValueError):
    def __init__(
        self,
        truck_count: int,
        max_trucks: int = MAX_COMPARISON_TRUCKS,
    ) -> None:
        self.truck_count = truck_count
        self.max_trucks = max_trucks
        super().__init__(
            f"comparison contains {truck_count} trucks; maximum is {max_trucks}"
        )


@dataclass(frozen=True)
class TruckComparisonCandidate:
    truck_id: UUID
    capacity: TruckCapacityInput

    def __post_init__(self) -> None:
        if not isinstance(self.truck_id, UUID):
            raise InvalidTruckComparisonInputError(
                "truck_id",
                "must be a UUID",
            )
        if not isinstance(self.capacity, TruckCapacityInput):
            raise InvalidTruckComparisonInputError(
                "capacity",
                "must be a TruckCapacityInput",
            )


@dataclass(frozen=True)
class TruckComparisonResult:
    truck_id: UUID
    load_plan: LoadPlanResult

    def __post_init__(self) -> None:
        if not isinstance(self.truck_id, UUID):
            raise InvalidTruckComparisonInputError(
                "truck_id",
                "must be a UUID",
            )
        if not isinstance(self.load_plan, LoadPlanResult):
            raise InvalidTruckComparisonInputError(
                "load_plan",
                "must be a LoadPlanResult",
            )


def _prepare_order_items(
    order_items: Sequence[OrderItemInput],
) -> tuple[OrderItemInput, ...]:
    if not isinstance(order_items, Sequence) or isinstance(
        order_items,
        (str, bytes, bytearray),
    ):
        raise InvalidTruckComparisonInputError(
            "order_items",
            "must be an ordered sequence of OrderItemInput",
        )

    prepared = tuple(order_items)
    if not prepared:
        raise InvalidTruckComparisonInputError(
            "order_items",
            "must not be empty",
        )

    volume_count = 0
    for position, item in enumerate(prepared):
        if not isinstance(item, OrderItemInput):
            raise InvalidTruckComparisonInputError(
                f"order_items[{position}]",
                "must be an OrderItemInput",
            )
        if (
            not isinstance(item.quantity, int)
            or isinstance(item.quantity, bool)
            or item.quantity <= 0
        ):
            raise InvalidTruckComparisonInputError(
                f"order_items[{position}].quantity",
                "must be a positive integer",
            )
        volume_count += item.quantity
        if volume_count > MAX_VOLUMES:
            raise LoadPlanVolumeLimitExceededError(volume_count)

    return prepared


def compare_trucks(
    candidates: Sequence[TruckComparisonCandidate],
    order_items: Sequence[OrderItemInput],
) -> tuple[TruckComparisonResult, ...]:
    """Calculate one independent load plan per candidate, without ranking them."""

    if not isinstance(candidates, Sequence) or isinstance(
        candidates,
        (str, bytes, bytearray),
    ):
        raise InvalidTruckComparisonInputError(
            "candidates",
            "must be an ordered sequence of TruckComparisonCandidate",
        )

    validated_candidates = tuple(candidates)
    truck_count = len(validated_candidates)
    if truck_count > MAX_COMPARISON_TRUCKS:
        raise TruckComparisonLimitExceededError(truck_count)

    for position, candidate in enumerate(validated_candidates):
        if not isinstance(candidate, TruckComparisonCandidate):
            raise InvalidTruckComparisonInputError(
                f"candidates[{position}]",
                "must be a TruckComparisonCandidate",
            )

    prepared_order_items = _prepare_order_items(order_items)
    if not validated_candidates:
        expand_order_items(prepared_order_items)
        return ()

    return tuple(
        TruckComparisonResult(
            truck_id=candidate.truck_id,
            load_plan=calculate_load_plan(candidate.capacity, prepared_order_items),
        )
        for candidate in validated_candidates
    )
