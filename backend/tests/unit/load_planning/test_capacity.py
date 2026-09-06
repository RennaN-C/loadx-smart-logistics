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
    assert isinstance(result.internal_volume_cm3, int)


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
        TruckCapacityInput(
            internal_width_cm=-1,
            internal_height_cm=260,
            internal_length_cm=600,
            max_weight_kg=Decimal("8000.00"),
        ),
        TruckCapacityInput(
            internal_width_cm=240,
            internal_height_cm=-1,
            internal_length_cm=600,
            max_weight_kg=Decimal("8000.00"),
        ),
        TruckCapacityInput(
            internal_width_cm=240,
            internal_height_cm=260,
            internal_length_cm=-1,
            max_weight_kg=Decimal("8000.00"),
        ),
        TruckCapacityInput(
            internal_width_cm=240,
            internal_height_cm=260,
            internal_length_cm=600,
            max_weight_kg=Decimal("-0.01"),
        ),
        TruckCapacityInput(
            internal_width_cm=240,
            internal_height_cm=260,
            internal_length_cm=600,
            max_weight_kg=Decimal("NaN"),
        ),
        TruckCapacityInput(
            internal_width_cm=240,
            internal_height_cm=260,
            internal_length_cm=600,
            max_weight_kg=Decimal("Infinity"),
        ),
    ],
)
def test_calculate_truck_capacity_rejects_invalid_values(
    truck: TruckCapacityInput,
) -> None:
    with pytest.raises(InvalidTruckCapacityError):
        calculate_truck_capacity(truck)


@pytest.mark.parametrize("invalid_weight", [8000, 8000.0, None])
def test_calculate_truck_capacity_rejects_non_decimal_weight(
    invalid_weight: object,
) -> None:
    truck = TruckCapacityInput(
        internal_width_cm=240,
        internal_height_cm=260,
        internal_length_cm=600,
        max_weight_kg=invalid_weight,  # type: ignore[arg-type]
    )

    with pytest.raises(InvalidTruckCapacityError):
        calculate_truck_capacity(truck)


@pytest.mark.parametrize(
    "field_name",
    ["internal_width_cm", "internal_height_cm", "internal_length_cm"],
)
@pytest.mark.parametrize(
    "invalid_dimension",
    [1.5, "1", True, None, Decimal(1)],
)
def test_calculate_truck_capacity_requires_integer_dimensions(
    field_name: str,
    invalid_dimension: object,
) -> None:
    values: dict[str, object] = {
        "internal_width_cm": 240,
        "internal_height_cm": 260,
        "internal_length_cm": 600,
        "max_weight_kg": Decimal("8000.00"),
    }
    values[field_name] = invalid_dimension
    truck = TruckCapacityInput(**values)  # type: ignore[arg-type]

    with pytest.raises(InvalidTruckCapacityError):
        calculate_truck_capacity(truck)
