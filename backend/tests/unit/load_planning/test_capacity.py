from decimal import Decimal

import pytest

from app.modules.load_planning.optimizer.capacity import (
    InvalidTruckCapacityError,
    TruckCapacityInput,
    TruckCapacityResult,
    calculate_truck_capacity,
)


def test_calculate_truck_capacity_returns_internal_volume_and_weight() -> None:
    truck = TruckCapacityInput(
        internal_width_cm=240,
        internal_height_cm=260,
        internal_length_cm=600,
        max_weight_kg=Decimal("8000.00"),
    )

    result = calculate_truck_capacity(truck)

    assert result == TruckCapacityResult(
        internal_width_cm=240,
        internal_height_cm=260,
        internal_length_cm=600,
        internal_volume_cm3=37_440_000,
        max_weight_kg=Decimal("8000.00"),
    )


def test_calculate_truck_capacity_is_deterministic() -> None:
    truck = TruckCapacityInput(
        internal_width_cm=240,
        internal_height_cm=260,
        internal_length_cm=600,
        max_weight_kg=Decimal("8000.00"),
    )

    first_result = calculate_truck_capacity(truck)
    second_result = calculate_truck_capacity(truck)

    assert first_result == second_result


@pytest.mark.parametrize(
    "truck",
    [
        TruckCapacityInput(
            internal_width_cm=0,
            internal_height_cm=260,
            internal_length_cm=600,
            max_weight_kg=Decimal("8000.00"),
        ),
        TruckCapacityInput(
            internal_width_cm=240,
            internal_height_cm=0,
            internal_length_cm=600,
            max_weight_kg=Decimal("8000.00"),
        ),
        TruckCapacityInput(
            internal_width_cm=240,
            internal_height_cm=260,
            internal_length_cm=0,
            max_weight_kg=Decimal("8000.00"),
        ),
        TruckCapacityInput(
            internal_width_cm=240,
            internal_height_cm=260,
            internal_length_cm=600,
            max_weight_kg=Decimal(0),
        ),
    ],
)
def test_calculate_truck_capacity_rejects_invalid_values(truck: TruckCapacityInput) -> None:
    with pytest.raises(InvalidTruckCapacityError):
        calculate_truck_capacity(truck)
