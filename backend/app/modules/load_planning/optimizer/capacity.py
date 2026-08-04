from dataclasses import dataclass
from decimal import Decimal


class InvalidTruckCapacityError(Exception):
    pass


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InvalidTruckCapacityError(f"{field_name} must be a positive integer")


@dataclass(frozen=True)
class TruckCapacityInput:
    internal_width_cm: int
    internal_height_cm: int
    internal_length_cm: int
    max_weight_kg: Decimal


@dataclass(frozen=True)
class TruckCapacityResult:
    internal_width_cm: int
    internal_height_cm: int
    internal_length_cm: int
    internal_volume_cm3: int
    max_weight_kg: Decimal


def calculate_truck_capacity(truck: TruckCapacityInput) -> TruckCapacityResult:
    _require_positive_int(truck.internal_width_cm, "internal_width_cm")
    _require_positive_int(truck.internal_height_cm, "internal_height_cm")
    _require_positive_int(truck.internal_length_cm, "internal_length_cm")
    if (
        not isinstance(truck.max_weight_kg, Decimal)
        or not truck.max_weight_kg.is_finite()
        or truck.max_weight_kg <= 0
    ):
        raise InvalidTruckCapacityError("max_weight_kg must be greater than zero")

    internal_volume_cm3 = (
        truck.internal_width_cm * truck.internal_height_cm * truck.internal_length_cm
    )
    return TruckCapacityResult(
        internal_width_cm=truck.internal_width_cm,
        internal_height_cm=truck.internal_height_cm,
        internal_length_cm=truck.internal_length_cm,
        internal_volume_cm3=internal_volume_cm3,
        max_weight_kg=truck.max_weight_kg,
    )
