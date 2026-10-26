"""Reproducible synthetic CPU benchmark; never connects to a database or provider."""

import argparse
import hashlib
import json
import math
import resource
import statistics
import time
import uuid
from dataclasses import asdict
from decimal import Decimal

from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import OrderItemInput
from app.modules.load_planning.optimizer.multi_truck import (
    MultiTruckCandidate,
    optimize_multi_truck,
)
from app.modules.load_planning.optimizer.volumes import expand_order_items


def run_case(
    volume_count: int, truck_count: int, *, force_trucks: bool
) -> dict[str, object]:
    items = tuple(
        OrderItemInput(
            order_id=uuid.UUID(int=100),
            order_item_id=uuid.UUID(int=200 + i),
            product_id=uuid.UUID(int=300 + i),
            quantity=volume_count // 2 + (volume_count % 2 if i == 0 else 0),
            delivery_sequence=1,
            width_cm=40 + i * 10,
            height_cm=40,
            length_cm=40,
            weight_kg=Decimal(10),
            fragile=bool(i),
            stackable=True,
            rotation_allowed=True,
        )
        for i in range(2)
    )
    volumes = expand_order_items(items)
    capacity = (
        TruckCapacityInput(
            50, 40, 40 * math.ceil(volume_count / truck_count), Decimal(5000)
        )
        if force_trucks
        else TruckCapacityInput(240, 260, 600, Decimal(5000))
    )
    trucks = tuple(
        MultiTruckCandidate(uuid.UUID(int=400 + i), capacity)
        for i in range(truck_count)
    )
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    result = optimize_multi_truck(trucks, volumes)
    elapsed, cpu_elapsed = (
        time.perf_counter() - wall_start,
        time.process_time() - cpu_start,
    )
    identities = [v.identity for part in result.parts for v in part.volumes] + [
        v.identity for v in result.remaining_volumes
    ]
    if len(identities) != len(set(identities)) or set(identities) != {
        v.identity for v in volumes
    }:
        raise RuntimeError("Physical volume conservation failed")
    physical = asdict(result)
    physical.pop("attempt_count")
    signature = hashlib.sha256(
        json.dumps(physical, sort_keys=True, default=str).encode()
    ).hexdigest()
    return {
        "volumes": volume_count,
        "candidates": truck_count,
        "parts": len(result.parts),
        "complete": result.complete,
        "seconds": elapsed,
        "cpu_seconds": cpu_elapsed,
        "engine_calls": result.attempt_count,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "physical_signature": signature,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volumes", type=int, choices=range(10, 201), default=50)
    parser.add_argument("--trucks", type=int, choices=range(1, 11), default=2)
    parser.add_argument("--repetitions", type=int, choices=range(1, 6), default=3)
    parser.add_argument(
        "--force-trucks",
        action="store_true",
        help="One layer; capacity sized to require the selected fleet",
    )
    args = parser.parse_args()
    rows = [
        run_case(args.volumes, args.trucks, force_trucks=args.force_trucks)
        for _ in range(args.repetitions)
    ]
    samples = sorted(float(row["seconds"]) for row in rows)
    print(
        json.dumps(
            {
                "fixture": "two synthetic products; one fragile; positive Decimal weights",
                "force_trucks": args.force_trucks,
                "p50_seconds": statistics.median(samples),
                "p95_nearest_rank_seconds": samples[math.ceil(0.95 * len(samples)) - 1],
                "samples": rows,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
