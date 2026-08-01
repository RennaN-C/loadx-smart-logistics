from decimal import Decimal

import pytest

from app.modules.load_planning.optimizer.weight import (
    InvalidWeightInputError,
    WeightLimitExceededError,
    calculate_next_weight,
)


def test_calculate_next_weight_returns_the_decimal_sum() -> None:
    result = calculate_next_weight(
        current_weight_kg=Decimal("12.125"),
        candidate_weight_kg=Decimal("0.375"),
        max_weight_kg=Decimal("20.000"),
    )

    assert result == Decimal("12.500")
    assert isinstance(result, Decimal)


def test_calculate_next_weight_accepts_weight_equal_to_the_maximum() -> None:
    assert calculate_next_weight(
        current_weight_kg=Decimal("7.500"),
        candidate_weight_kg=Decimal("2.500"),
        max_weight_kg=Decimal("10.000"),
    ) == Decimal("10.000")


def test_calculate_next_weight_accumulates_multiple_volumes_without_float_loss() -> (
    None
):
    max_weight = Decimal("0.600")
    total = Decimal("0.000")

    for candidate_weight in (Decimal("0.100"), Decimal("0.200"), Decimal("0.300")):
        total = calculate_next_weight(total, candidate_weight, max_weight)

    assert total == Decimal("0.600")


def test_calculate_next_weight_is_deterministic() -> None:
    arguments = {
        "current_weight_kg": Decimal("10.125"),
        "candidate_weight_kg": Decimal("2.375"),
        "max_weight_kg": Decimal("20.000"),
    }

    first_result = calculate_next_weight(**arguments)
    second_result = calculate_next_weight(**arguments)

    assert first_result == second_result == Decimal("12.500")


def test_calculate_next_weight_rejects_excess_without_changing_the_current_weight() -> (
    None
):
    current_weight = Decimal("9.500")

    with pytest.raises(WeightLimitExceededError) as exc_info:
        calculate_next_weight(
            current_weight_kg=current_weight,
            candidate_weight_kg=Decimal("0.501"),
            max_weight_kg=Decimal("10.000"),
        )

    assert current_weight == Decimal("9.500")
    assert exc_info.value.current_weight_kg == Decimal("9.500")
    assert exc_info.value.candidate_weight_kg == Decimal("0.501")
    assert exc_info.value.max_weight_kg == Decimal("10.000")
    assert exc_info.value.next_total_weight_kg == Decimal("10.001")


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("current_weight_kg", 0),
        ("candidate_weight_kg", 1),
        ("max_weight_kg", 10),
        ("current_weight_kg", Decimal("NaN")),
        ("candidate_weight_kg", Decimal("Infinity")),
        ("max_weight_kg", Decimal("-Infinity")),
    ],
)
def test_calculate_next_weight_requires_finite_decimals(
    field_name: str, invalid_value: object
) -> None:
    arguments: dict[str, object] = {
        "current_weight_kg": Decimal("0.000"),
        "candidate_weight_kg": Decimal("1.000"),
        "max_weight_kg": Decimal("10.000"),
    }
    arguments[field_name] = invalid_value

    with pytest.raises(InvalidWeightInputError) as exc_info:
        calculate_next_weight(**arguments)  # type: ignore[arg-type]

    assert exc_info.value.field_name == field_name


@pytest.mark.parametrize("max_weight", [Decimal(0), Decimal("-0.001")])
def test_calculate_next_weight_requires_a_positive_maximum(max_weight: Decimal) -> None:
    with pytest.raises(InvalidWeightInputError) as exc_info:
        calculate_next_weight(Decimal(0), Decimal(1), max_weight)

    assert exc_info.value.field_name == "max_weight_kg"


@pytest.mark.parametrize("current_weight", [Decimal("-0.001"), Decimal("10.001")])
def test_calculate_next_weight_requires_a_valid_current_total(
    current_weight: Decimal,
) -> None:
    with pytest.raises(InvalidWeightInputError) as exc_info:
        calculate_next_weight(current_weight, Decimal(1), Decimal(10))

    assert exc_info.value.field_name == "current_weight_kg"


@pytest.mark.parametrize("candidate_weight", [Decimal(0), Decimal("-0.001")])
def test_calculate_next_weight_requires_a_positive_candidate(
    candidate_weight: Decimal,
) -> None:
    with pytest.raises(InvalidWeightInputError) as exc_info:
        calculate_next_weight(Decimal(0), candidate_weight, Decimal(10))

    assert exc_info.value.field_name == "candidate_weight_kg"
