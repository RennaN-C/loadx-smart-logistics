from decimal import Decimal

import pytest

from benchmarks.benchmark_truck_comparison import (
    TRUCK_COUNTS,
    VOLUME_COUNTS,
    build_benchmark_case,
    validate_comparison_result,
)


@pytest.mark.parametrize("truck_count", TRUCK_COUNTS)
@pytest.mark.parametrize("volume_count", VOLUME_COUNTS)
def test_benchmark_case_generator_builds_the_required_matrix(
    truck_count: int,
    volume_count: int,
) -> None:
    case = build_benchmark_case(truck_count, volume_count)

    assert case.truck_count == truck_count
    assert case.volume_count == volume_count
    assert len(case.candidates) == truck_count
    assert len({candidate.truck_id for candidate in case.candidates}) == truck_count
    assert sum(item.quantity for item in case.order_items) == volume_count
    assert all(
        candidate.capacity.max_weight_kg == Decimal("10.00")
        for candidate in case.candidates
    )


@pytest.mark.parametrize("truck_count", [0, 1, 3, 11])
def test_benchmark_case_generator_rejects_truck_counts_outside_matrix(
    truck_count: int,
) -> None:
    with pytest.raises(ValueError, match="truck_count"):
        build_benchmark_case(truck_count, 10)


@pytest.mark.parametrize("volume_count", [0, 1, 201])
def test_benchmark_case_generator_rejects_volume_counts_outside_matrix(
    volume_count: int,
) -> None:
    with pytest.raises(ValueError, match="volume_count"):
        build_benchmark_case(2, volume_count)


def test_benchmark_result_validation_rejects_missing_trucks() -> None:
    case = build_benchmark_case(2, 10)

    with pytest.raises(RuntimeError, match="number of trucks"):
        validate_comparison_result(case, ())
