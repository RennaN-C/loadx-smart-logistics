"""Basic OC21 benchmark for the pure truck-comparison operation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from decimal import Decimal
from statistics import mean, median
from time import perf_counter
from typing import Any
from uuid import UUID

from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.comparison import (
    TruckComparisonCandidate,
    TruckComparisonResult,
    compare_trucks,
)
from app.modules.load_planning.optimizer.contracts import OrderItemInput

TRUCK_COUNTS = (2, 5, 10)
VOLUME_COUNTS = (10, 50, 100, 200)
EXPECTED_ALGORITHM_VERSION = "heuristic-v1"


@dataclass(frozen=True)
class BenchmarkCase:
    truck_count: int
    volume_count: int
    candidates: tuple[TruckComparisonCandidate, ...]
    order_items: tuple[OrderItemInput, ...]


@dataclass(frozen=True)
class BenchmarkResult:
    truck_count: int
    volume_count: int
    engine_runs_per_iteration: int
    evaluated_volumes_per_iteration: int
    warmup_iterations: int
    measured_iterations: int
    min_ms: float
    median_ms: float
    mean_ms: float
    max_ms: float
    median_per_truck_ms: float
    median_per_volume_truck_us: float


def build_benchmark_case(truck_count: int, volume_count: int) -> BenchmarkCase:
    """Build deterministic, synthetic inputs without database or HTTP access."""

    if truck_count not in TRUCK_COUNTS:
        raise ValueError(f"truck_count must be one of {TRUCK_COUNTS}")
    if volume_count not in VOLUME_COUNTS:
        raise ValueError(f"volume_count must be one of {VOLUME_COUNTS}")

    candidates = tuple(
        TruckComparisonCandidate(
            truck_id=UUID(int=truck_position + 1),
            capacity=TruckCapacityInput(
                internal_width_cm=220 + (truck_position % 3) * 10,
                internal_height_cm=240 + (truck_position % 2) * 10,
                internal_length_cm=500 + truck_position * 10,
                max_weight_kg=Decimal("10.00"),
            ),
        )
        for truck_position in range(truck_count)
    )
    order_items = (
        OrderItemInput(
            order_id=UUID(int=10_001),
            order_item_id=UUID(int=20_001),
            product_id=UUID(int=30_001),
            quantity=volume_count,
            delivery_sequence=1,
            width_cm=20,
            height_cm=20,
            length_cm=20,
            weight_kg=Decimal("2.000"),
            fragile=False,
            stackable=True,
            rotation_allowed=True,
            product_name="Synthetic benchmark volume",
        ),
    )
    return BenchmarkCase(
        truck_count=truck_count,
        volume_count=volume_count,
        candidates=candidates,
        order_items=order_items,
    )


def validate_comparison_result(
    case: BenchmarkCase,
    results: Sequence[TruckComparisonResult],
) -> None:
    """Fail the benchmark if a case does not satisfy the OC21 invariants."""

    if len(results) != case.truck_count:
        raise RuntimeError("comparison returned an unexpected number of trucks")
    if tuple(result.truck_id for result in results) != tuple(
        candidate.truck_id for candidate in case.candidates
    ):
        raise RuntimeError("comparison did not preserve candidate order")

    for result in results:
        metrics = result.load_plan.metrics
        if metrics.loaded_count + metrics.unloaded_count != case.volume_count:
            raise RuntimeError("comparison did not account for every input volume")
        if metrics.algorithm_version != EXPECTED_ALGORITHM_VERSION:
            raise RuntimeError("comparison returned an unexpected algorithm version")
        if metrics.loaded_count != 5:
            raise RuntimeError("synthetic case must load exactly five volumes")
        if metrics.unloaded_count != case.volume_count - 5:
            raise RuntimeError("synthetic case returned unexpected rejection count")


def run_benchmark_case(
    case: BenchmarkCase,
    *,
    warmup_iterations: int,
    measured_iterations: int,
    timer: Callable[[], float] = perf_counter,
) -> BenchmarkResult:
    if warmup_iterations < 0:
        raise ValueError("warmup_iterations must be greater than or equal to zero")
    if measured_iterations <= 0:
        raise ValueError("measured_iterations must be greater than zero")

    for _ in range(warmup_iterations):
        warmup_result = compare_trucks(case.candidates, case.order_items)
        validate_comparison_result(case, warmup_result)

    timings_ms: list[float] = []
    for _ in range(measured_iterations):
        started_at = timer()
        result = compare_trucks(case.candidates, case.order_items)
        finished_at = timer()
        validate_comparison_result(case, result)
        timings_ms.append((finished_at - started_at) * 1_000)

    median_ms = median(timings_ms)
    evaluated_volumes = case.truck_count * case.volume_count
    return BenchmarkResult(
        truck_count=case.truck_count,
        volume_count=case.volume_count,
        engine_runs_per_iteration=case.truck_count,
        evaluated_volumes_per_iteration=evaluated_volumes,
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        min_ms=min(timings_ms),
        median_ms=median_ms,
        mean_ms=mean(timings_ms),
        max_ms=max(timings_ms),
        median_per_truck_ms=median_ms / case.truck_count,
        median_per_volume_truck_us=(median_ms * 1_000) / evaluated_volumes,
    )


def run_benchmark_matrix(
    *,
    warmup_iterations: int = 1,
    measured_iterations: int = 3,
) -> tuple[BenchmarkResult, ...]:
    return tuple(
        run_benchmark_case(
            build_benchmark_case(truck_count, volume_count),
            warmup_iterations=warmup_iterations,
            measured_iterations=measured_iterations,
        )
        for truck_count in TRUCK_COUNTS
        for volume_count in VOLUME_COUNTS
    )


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _non_negative_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to zero")
    return parsed


def _json_payload(
    results: Sequence[BenchmarkResult],
    *,
    warmup_iterations: int,
    measured_iterations: int,
) -> dict[str, Any]:
    return {
        "benchmark": "oc21-truck-comparison",
        "algorithm_version": EXPECTED_ALGORITHM_VERSION,
        "timer": "time.perf_counter",
        "warmup_iterations": warmup_iterations,
        "measured_iterations": measured_iterations,
        "cases": [asdict(result) for result in results],
    }


def _format_table(results: Sequence[BenchmarkResult]) -> str:
    headers = (
        "trucks",
        "volumes",
        "evaluations",
        "min_ms",
        "median_ms",
        "mean_ms",
        "max_ms",
        "ms/truck",
        "us/volume-truck",
    )
    rows = [
        (
            str(result.truck_count),
            str(result.volume_count),
            str(result.evaluated_volumes_per_iteration),
            f"{result.min_ms:.3f}",
            f"{result.median_ms:.3f}",
            f"{result.mean_ms:.3f}",
            f"{result.max_ms:.3f}",
            f"{result.median_per_truck_ms:.3f}",
            f"{result.median_per_volume_truck_us:.3f}",
        )
        for result in results
    ]
    widths = tuple(
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    )
    formatted_header = "  ".join(
        header.rjust(widths[index]) for index, header in enumerate(headers)
    )
    separator = "  ".join("-" * width for width in widths)
    formatted_rows = [
        "  ".join(value.rjust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]
    return "\n".join((formatted_header, separator, *formatted_rows))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the OC21 pure truck-comparison benchmark matrix.",
    )
    parser.add_argument(
        "--warmup",
        type=_non_negative_integer,
        default=1,
        help="warmup iterations per case (default: 1)",
    )
    parser.add_argument(
        "--iterations",
        type=_positive_integer,
        default=3,
        help="measured iterations per case (default: 3)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of the table",
    )
    args = parser.parse_args(argv)

    results = run_benchmark_matrix(
        warmup_iterations=args.warmup,
        measured_iterations=args.iterations,
    )
    if args.json:
        print(
            json.dumps(
                _json_payload(
                    results,
                    warmup_iterations=args.warmup,
                    measured_iterations=args.iterations,
                ),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(
            f"OC21 truck comparison ({EXPECTED_ALGORITHM_VERSION}); "
            f"warmup={args.warmup}; iterations={args.iterations}"
        )
        print(_format_table(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
