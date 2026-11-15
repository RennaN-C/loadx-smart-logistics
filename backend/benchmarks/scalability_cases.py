"""Deterministic, synthetic physical workloads for Issue #430 (no I/O)."""

from dataclasses import dataclass
from decimal import Decimal
from math import ceil
from uuid import UUID

from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import OrderItemInput

PROFILES = (
    "homogeneous",
    "heterogeneous",
    "non_stackable",
    "fragile",
    "deliveries",
    "fleet",
    "over_capacity",
    "dense",
    "distribution",
    "adversarial",
)


@dataclass(frozen=True)
class ScalabilityCase:
    items: tuple[OrderItemInput, ...]
    trucks: tuple[TruckCapacityInput, ...]


def build_case(profile: str, count: int, truck_count: int) -> ScalabilityCase:
    if profile not in PROFILES or count <= 0 or not 1 <= truck_count <= 10:
        raise ValueError("invalid synthetic case")
    items = []
    for index in range(count):
        heterogeneous = profile in {"heterogeneous", "adversarial", "fleet"}
        width, height, length = (
            (7 + index % 7, 8 + index % 5, 9 + index % 11)
            if heterogeneous
            else (10, 10, 10)
        )
        items.append(
            OrderItemInput(
                order_id=UUID(int=10_000 + index % 5),
                order_item_id=UUID(int=20_000 + index),
                product_id=UUID(int=30_000 + index % 11),
                quantity=1,
                delivery_sequence=1 + (index % 5 if profile == "deliveries" else 0),
                width_cm=width,
                height_cm=height,
                length_cm=length,
                weight_kg=Decimal("1.25"),
                fragile=profile == "fragile" and index % 3 == 0,
                stackable=profile not in {"non_stackable", "distribution"},
                rotation_allowed=heterogeneous,
                product_name="Synthetic Issue 430",
            )
        )
    trucks = []
    for index in range(truck_count):
        width, height, length = 100, 100, max(100, ceil(count / 100) * 10)
        if profile == "non_stackable":
            height, length = 10, ceil(count / 10) * 10
        elif profile == "distribution":
            # Exactly ceil(n/k) floor slots per vehicle; >1 truck is necessary.
            width, height, length = 10, 10, ceil(count / truck_count) * 10
        elif profile == "dense":
            width, height, length = 50, 50, ceil(count / 25) * 10
        elif profile == "over_capacity":
            width, height, length = 30, 20, max(10, count // 12 * 10)
        elif profile == "adversarial":
            width, height, length = 47, 43, max(30, ceil(count / 16) * 11)
        elif profile == "fleet":
            width, height, length = (
                40 + index * 7,
                30 + index * 3,
                max(30, ceil(count / 40) * 10),
            )
        trucks.append(TruckCapacityInput(width, height, length, Decimal(100000)))
    return ScalabilityCase(tuple(items), tuple(trucks))
