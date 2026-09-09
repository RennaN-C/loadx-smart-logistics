from dataclasses import FrozenInstanceError
from decimal import Decimal, Inexact, Rounded, localcontext
from itertools import permutations
from uuid import UUID

import pytest

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.metrics import (
    ALGORITHM_VERSION,
    InvalidMetricsInputError,
    LoadMetrics,
    calculate_load_metrics,
)


def make_volume(identity_number: int, **overrides: object) -> IndividualVolume:
    values: dict[str, object] = {
        "identity": VolumeIdentity(
            order_item_id=UUID(int=identity_number),
            volume_index=1,
        ),
        "order_id": UUID(int=100 + identity_number),
        "product_id": UUID(int=200 + identity_number),
        "product_name": f"Volume {identity_number}",
        "delivery_sequence": 1,
        "original_width_cm": 10,
        "original_height_cm": 10,
        "original_length_cm": 10,
        "volume_cm3": 1_000,
        "weight_kg": Decimal("1.000"),
        "fragile": False,
        "stackable": True,
        "rotation_allowed": True,
    }
    values.update(overrides)
    return IndividualVolume(**values)  # type: ignore[arg-type]


def test_empty_load_has_zero_metrics_with_two_decimal_occupancy() -> None:
    result = calculate_load_metrics(
        internal_volume_cm3=10_000,
        placed_volumes=[],
        rejected_volumes=[],
    )

    assert result == LoadMetrics(
        internal_volume_cm3=10_000,
        used_volume_cm3=0,
        total_weight_kg=Decimal(0),
        occupancy_percent=Decimal("0.00"),
        loaded_count=0,
        unloaded_count=0,
        algorithm_version="heuristic-v1",
    )
    assert result.occupancy_percent.as_tuple().exponent == -2


def test_partial_load_uses_only_placed_volume_and_weight() -> None:
    placed = make_volume(
        1,
        volume_cm3=2_500,
        weight_kg=Decimal("12.125"),
    )
    rejected = make_volume(
        2,
        volume_cm3=50_000,
        weight_kg=Decimal("999.999"),
    )

    result = calculate_load_metrics(
        internal_volume_cm3=10_000,
        placed_volumes=[placed],
        rejected_volumes=[rejected],
    )

    assert result.internal_volume_cm3 == 10_000
    assert result.used_volume_cm3 == 2_500
    assert result.total_weight_kg == Decimal("12.125")
    assert result.occupancy_percent == Decimal("25.00")
    assert result.loaded_count == 1
    assert result.unloaded_count == 1


def test_full_load_returns_exactly_one_hundred_percent() -> None:
    result = calculate_load_metrics(
        internal_volume_cm3=2_000,
        placed_volumes=[make_volume(1), make_volume(2)],
        rejected_volumes=[],
    )

    assert result.used_volume_cm3 == 2_000
    assert result.occupancy_percent == Decimal("100.00")
    assert result.occupancy_percent.as_tuple().exponent == -2


def test_occupancy_rounds_half_up_only_after_the_total_is_calculated() -> None:
    result = calculate_load_metrics(
        internal_volume_cm3=64,
        placed_volumes=[
            make_volume(1, volume_cm3=1),
            make_volume(2, volume_cm3=1),
        ],
        rejected_volumes=[],
    )

    assert result.occupancy_percent == Decimal("3.13")


def test_metrics_sum_fractional_placed_weights_without_float_loss() -> None:
    placed = [
        make_volume(1, volume_cm3=1, weight_kg=Decimal("0.100")),
        make_volume(2, volume_cm3=1, weight_kg=Decimal("0.200")),
        make_volume(3, volume_cm3=1, weight_kg=Decimal("0.300")),
    ]

    result = calculate_load_metrics(
        internal_volume_cm3=10,
        placed_volumes=placed,
        rejected_volumes=[],
    )

    assert result.total_weight_kg == Decimal("0.600")


def test_metrics_are_independent_of_collection_order() -> None:
    placed = (
        make_volume(1, volume_cm3=1, weight_kg=Decimal("0.100")),
        make_volume(2, volume_cm3=2, weight_kg=Decimal("0.200")),
        make_volume(3, volume_cm3=3, weight_kg=Decimal("0.300")),
    )
    rejected = (make_volume(4), make_volume(5))
    expected = calculate_load_metrics(
        internal_volume_cm3=20,
        placed_volumes=placed,
        rejected_volumes=rejected,
    )

    for placed_order in permutations(placed):
        for rejected_order in permutations(rejected):
            assert (
                calculate_load_metrics(
                    internal_volume_cm3=20,
                    placed_volumes=placed_order,
                    rejected_volumes=rejected_order,
                )
                == expected
            )


def test_metrics_do_not_mutate_input_collections() -> None:
    placed = [make_volume(2), make_volume(1)]
    rejected = [make_volume(3)]
    original_placed = list(placed)
    original_rejected = list(rejected)

    calculate_load_metrics(
        internal_volume_cm3=10_000,
        placed_volumes=placed,
        rejected_volumes=rejected,
    )

    assert placed == original_placed
    assert rejected == original_rejected


def test_metrics_ignore_the_ambient_decimal_context() -> None:
    with localcontext() as context:
        context.prec = 2
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        result = calculate_load_metrics(
            internal_volume_cm3=32,
            placed_volumes=[
                make_volume(1, volume_cm3=1, weight_kg=Decimal("999.999")),
                make_volume(2, volume_cm3=1, weight_kg=Decimal("0.001")),
            ],
            rejected_volumes=[],
        )

    assert result.total_weight_kg == Decimal("1000.000")
    assert result.occupancy_percent == Decimal("6.25")


def test_metrics_expose_the_approved_initial_algorithm_version() -> None:
    result = calculate_load_metrics(
        internal_volume_cm3=1,
        placed_volumes=[],
        rejected_volumes=[],
    )

    assert ALGORITHM_VERSION == "heuristic-v1"
    assert result.algorithm_version == ALGORITHM_VERSION


def test_load_metrics_is_immutable() -> None:
    result = calculate_load_metrics(
        internal_volume_cm3=1,
        placed_volumes=[],
        rejected_volumes=[],
    )

    with pytest.raises(FrozenInstanceError):
        result.loaded_count = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "invalid_internal_volume",
    [0, -1, True, 1.0, Decimal(1)],
)
def test_metrics_require_a_positive_integer_internal_volume(
    invalid_internal_volume: object,
) -> None:
    with pytest.raises(InvalidMetricsInputError) as exc_info:
        calculate_load_metrics(
            internal_volume_cm3=invalid_internal_volume,  # type: ignore[arg-type]
            placed_volumes=[],
            rejected_volumes=[],
        )

    assert exc_info.value.code == "INVALID_METRICS_INPUT"
    assert exc_info.value.field_name == "internal_volume_cm3"


@pytest.mark.parametrize(
    ("field_name", "invalid_sequence"),
    [
        ("placed_volumes", "invalid"),
        ("placed_volumes", {make_volume(1)}),
        ("rejected_volumes", b"invalid"),
        ("rejected_volumes", (make_volume(1) for _ in range(1))),
    ],
)
def test_metrics_require_ordered_volume_sequences(
    field_name: str,
    invalid_sequence: object,
) -> None:
    arguments: dict[str, object] = {
        "internal_volume_cm3": 10_000,
        "placed_volumes": [],
        "rejected_volumes": [],
    }
    arguments[field_name] = invalid_sequence

    with pytest.raises(InvalidMetricsInputError) as exc_info:
        calculate_load_metrics(**arguments)  # type: ignore[arg-type]

    assert exc_info.value.field_name == field_name


@pytest.mark.parametrize("field_name", ["placed_volumes", "rejected_volumes"])
def test_metrics_require_individual_volume_elements(field_name: str) -> None:
    arguments: dict[str, object] = {
        "internal_volume_cm3": 10_000,
        "placed_volumes": [],
        "rejected_volumes": [],
    }
    arguments[field_name] = [object()]

    with pytest.raises(InvalidMetricsInputError) as exc_info:
        calculate_load_metrics(**arguments)  # type: ignore[arg-type]

    assert exc_info.value.field_name == f"{field_name}[0]"


@pytest.mark.parametrize(
    "invalid_volume_cm3",
    [0, -1, True, Decimal(1)],
)
def test_metrics_require_positive_integer_physical_volumes(
    invalid_volume_cm3: object,
) -> None:
    with pytest.raises(InvalidMetricsInputError) as exc_info:
        calculate_load_metrics(
            internal_volume_cm3=10_000,
            placed_volumes=[make_volume(1, volume_cm3=invalid_volume_cm3)],
            rejected_volumes=[],
        )

    assert exc_info.value.field_name == "placed_volumes[0].volume_cm3"


@pytest.mark.parametrize(
    "invalid_weight",
    [1, Decimal(0), Decimal("-0.001"), Decimal("NaN"), Decimal("Infinity")],
)
@pytest.mark.parametrize("field_name", ["placed_volumes", "rejected_volumes"])
def test_metrics_require_positive_finite_decimal_weights(
    field_name: str,
    invalid_weight: object,
) -> None:
    arguments: dict[str, object] = {
        "internal_volume_cm3": 10_000,
        "placed_volumes": [],
        "rejected_volumes": [],
    }
    arguments[field_name] = [make_volume(1, weight_kg=invalid_weight)]

    with pytest.raises(InvalidMetricsInputError) as exc_info:
        calculate_load_metrics(**arguments)  # type: ignore[arg-type]

    assert exc_info.value.field_name == f"{field_name}[0].weight_kg"


@pytest.mark.parametrize(
    "invalid_identity",
    [
        object(),
        VolumeIdentity(order_item_id="not-a-uuid", volume_index=1),
        VolumeIdentity(order_item_id=UUID(int=1), volume_index=0),
    ],
)
def test_metrics_require_valid_volume_identities(invalid_identity: object) -> None:
    with pytest.raises(InvalidMetricsInputError):
        calculate_load_metrics(
            internal_volume_cm3=10_000,
            placed_volumes=[make_volume(1, identity=invalid_identity)],
            rejected_volumes=[],
        )


@pytest.mark.parametrize(
    ("placed_volumes", "rejected_volumes", "field_name"),
    [
        ([make_volume(1), make_volume(1)], [], "placed_volumes[1].identity"),
        ([], [make_volume(1), make_volume(1)], "rejected_volumes[1].identity"),
        ([make_volume(1)], [make_volume(1)], "rejected_volumes[0].identity"),
    ],
)
def test_metrics_require_unique_disjoint_volume_identities(
    placed_volumes: list[IndividualVolume],
    rejected_volumes: list[IndividualVolume],
    field_name: str,
) -> None:
    with pytest.raises(InvalidMetricsInputError) as exc_info:
        calculate_load_metrics(
            internal_volume_cm3=10_000,
            placed_volumes=placed_volumes,
            rejected_volumes=rejected_volumes,
        )

    assert exc_info.value.field_name == field_name


def test_metrics_reject_placed_volume_above_internal_capacity() -> None:
    with pytest.raises(InvalidMetricsInputError) as exc_info:
        calculate_load_metrics(
            internal_volume_cm3=1_999,
            placed_volumes=[make_volume(1), make_volume(2)],
            rejected_volumes=[],
        )

    assert exc_info.value.field_name == "placed_volumes"
    assert "must not exceed" in exc_info.value.reason
