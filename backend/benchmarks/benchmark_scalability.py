"""Manual isolated benchmark. No production limit or application state is changed."""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict, is_dataclass
from decimal import ROUND_HALF_UP, Decimal
from itertools import product
from pathlib import Path
from uuid import UUID


class _InterruptedCase(Exception):
    def __init__(self, row: dict) -> None:
        self.row = row


def canonical(value):
    if is_dataclass(value):
        return canonical(asdict(value))
    if isinstance(value, dict):
        return {str(key): canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return value


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(canonical(value), sort_keys=True).encode()
    ).hexdigest()


def _check_shape(row, plan) -> None:
    from itertools import permutations

    x, y, z = row.position_x_cm, row.position_y_cm, row.position_z_cm
    w, h, length = row.used_width_cm, row.used_height_cm, row.used_length_cm
    original = (
        row.volume.original_width_cm,
        row.volume.original_height_cm,
        row.volume.original_length_cm,
    )
    assert (w, h, length) in (
        set(permutations(original)) if row.volume.rotation_allowed else {original}
    )
    assert min(x, y, z) >= 0
    assert x + w <= plan.capacity.internal_width_cm
    assert y + h <= plan.capacity.internal_height_cm
    assert z + length <= plan.capacity.internal_length_cm


def _check_support(row, tops, ancestors) -> set:
    supporters = set()
    if row.position_y_cm == 0:
        return supporters
    x, y, z = row.position_x_cm, row.position_y_cm, row.position_z_cm
    for a in range(x, x + row.used_width_cm):
        for c in range(z, z + row.used_length_cm):
            assert (a, y, c) in tops
            lower = tops[a, y, c]
            assert lower.volume.stackable and not lower.volume.fragile
            assert lower.loading_sequence < row.loading_sequence
            supporters.add(lower.identity)
            supporters.update(ancestors[lower.identity])
    return supporters


def _check_placed_box(row, plan, occupied, tops, ancestors) -> None:
    _check_shape(row, plan)
    x, y, z = row.position_x_cm, row.position_y_cm, row.position_z_cm
    w, h, length = row.used_width_cm, row.used_height_cm, row.used_length_cm
    cells = {
        (a, b, c)
        for a in range(x, x + w)
        for b in range(y, y + h)
        for c in range(z, z + length)
    }
    assert not occupied.intersection(cells)
    occupied.update(cells)
    ancestors[row.identity] = _check_support(row, tops, ancestors)
    for a in range(x, x + w):
        for c in range(z, z + length):
            tops[a, y + h, c] = row


def _check_delivery_depth(placed) -> None:
    from itertools import combinations

    for first, second in combinations(placed, 2):
        if first.volume.delivery_sequence == second.volume.delivery_sequence:
            continue
        later, earlier = sorted(
            (first, second), key=lambda row: -row.volume.delivery_sequence
        )
        assert (
            later.position_z_cm + later.used_length_cm
            <= earlier.position_z_cm + earlier.used_length_cm
        )


def _physical_check(plan, source) -> None:
    """Independent integer-cell oracle; checks the complete physical result."""

    placed, rejected = plan.placed_volumes, plan.rejected_volumes
    identities = [row.identity for row in (*placed, *rejected)]
    assert len(identities) == len(set(identities)) == len(source)
    assert set(identities) == {volume.identity for volume in source}
    assert {row.volume for row in (*placed, *rejected)} == set(source)
    occupied = set()
    tops = {}
    ancestors = {}
    for row in sorted(placed, key=lambda row: row.position_y_cm):
        _check_placed_box(row, plan, occupied, tops, ancestors)
    by_id = {row.identity: row for row in placed}
    assert all(
        not by_id[identity].volume.fragile
        for ids in ancestors.values()
        for identity in ids
    )
    _check_delivery_depth(placed)
    assert sorted(row.loading_sequence for row in placed) == list(
        range(1, len(placed) + 1)
    )
    assert (
        sum((row.volume.weight_kg for row in placed), Decimal(0))
        == plan.metrics.total_weight_kg
        <= plan.capacity.max_weight_kg
    )
    assert sum(row.volume.volume_cm3 for row in placed) == plan.metrics.used_volume_cm3
    expected_occupancy = (
        Decimal(plan.metrics.used_volume_cm3) * 100 / plan.capacity.internal_volume_cm3
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert plan.metrics.occupancy_percent == expected_occupancy
    assert plan.metrics.loaded_count == len(placed)
    assert plan.metrics.unloaded_count == len(rejected)


def _make_calculator(args, case, volumes, comparison, engine, multi_truck):
    def calculate():
        if args.operation == "engine":
            return engine.calculate_load_plan(case.trucks[0], case.items)
        if args.operation == "multi":
            return multi_truck.optimize_multi_truck(
                tuple(
                    multi_truck.MultiTruckCandidate(UUID(int=index + 1), truck)
                    for index, truck in enumerate(case.trucks)
                ),
                volumes,
            )
        return comparison.compare_trucks(
            tuple(
                comparison.TruckComparisonCandidate(UUID(int=index + 1), truck)
                for index, truck in enumerate(case.trucks)
            ),
            case.items,
        )

    return calculate


def _start_profiler(counts, loading_sequence, multi_truck):
    # Instrumentation applies only to the isolated benchmark worker.
    original_pairs = getattr(loading_sequence, "combinations", None)
    if original_pairs is not None:

        def pairs(*arguments):
            for pair in original_pairs(*arguments):
                counts["depth_pair_visits"] += 1
                yield pair

        loading_sequence.combinations = pairs
    original_state = multi_truck._SearchState

    def state(**kwargs):
        counts["search_states_created"] += 1
        return original_state(**kwargs)

    multi_truck._SearchState = state
    profiler = cProfile.Profile()
    profiler.enable()
    return profiler


def _checked_plans(args, result, volumes):
    if args.operation == "engine":
        plans, remaining, attempts = (result,), result.rejected_volumes, 1
    elif args.operation == "multi":
        plans = tuple(part.load_plan for part in result.parts)
        remaining, attempts = result.remaining_volumes, result.attempt_count
        ids = [volume.identity for part in result.parts for volume in part.volumes]
        ids.extend(volume.identity for volume in remaining)
        assert len(ids) == len(set(ids)) == len(volumes)
        assert set(ids) == {volume.identity for volume in volumes}
        assert all(
            set(part.volumes) == {row.volume for row in part.load_plan.placed_volumes}
            for part in result.parts
        )
    else:
        plans, remaining, attempts = (
            tuple(row.load_plan for row in result),
            (),
            args.trucks,
        )
    for plan in plans:
        # A multi search result also includes rejected volumes of this trial.
        plan_ids = {
            row.identity for row in (*plan.placed_volumes, *plan.rejected_volumes)
        }
        source = tuple(volume for volume in volumes if volume.identity in plan_ids)
        _physical_check(plan, source if args.operation == "multi" else volumes)
    return plans, remaining, attempts


def _profile_rows(profiler, counts) -> list[dict]:
    if not profiler:
        return []
    import pstats

    profile_rows = []
    for (filename, line, name), (
        primitive,
        calls,
        own,
        cumulative,
        _,
    ) in pstats.Stats(profiler).stats.items():
        if "/optimizer/" in filename:
            counts[name] += calls
            profile_rows.append(
                {
                    "file": Path(filename).name,
                    "line": line,
                    "function": name,
                    "calls": calls,
                    "own_s": own,
                    "cumulative_s": cumulative,
                }
            )
    profile_rows.sort(key=lambda row: -row["cumulative_s"])
    return profile_rows


def worker(args) -> dict:
    import resource

    # The alternate checkout is used ONLY by this isolated manual runner/oracle.
    sys.path.insert(0, str(Path(args.backend_root).resolve()))
    from app.modules.load_planning.optimizer import (
        comparison,
        engine,
        loading_sequence,
        multi_truck,
    )
    from app.modules.load_planning.optimizer.volumes import expand_order_items
    from benchmarks.scalability_cases import build_case

    if args.experimental_limit:
        engine.MAX_VOLUMES = comparison.MAX_VOLUMES = args.count
    case = build_case(args.profile, args.count, args.trucks)
    volumes = expand_order_items(case.items)

    calculate = _make_calculator(args, case, volumes, comparison, engine, multi_truck)

    counts = Counter()
    profiler = None
    if args.instrument:
        profiler = _start_profiler(counts, loading_sequence, multi_truck)
    elif args.allocations:
        import tracemalloc

        tracemalloc.start()
    else:
        for _ in range(args.warmup):
            calculate()
    samples = []
    fingerprints = []
    result = None
    for _ in range(1 if args.instrument or args.allocations else args.iterations):
        started = time.perf_counter()
        result = calculate()
        samples.append(time.perf_counter() - started)
        if not args.instrument and not args.allocations:
            fingerprints.append(fingerprint(result))
    if profiler:
        profiler.disable()
    assert not fingerprints or len(set(fingerprints)) == 1
    rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    allocation_peak = None
    if args.allocations:
        allocation_peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    plans, remaining, attempts = _checked_plans(args, result, volumes)
    profile_rows = _profile_rows(profiler, counts)
    return {
        "status": "incomplete_valid"
        if args.operation == "multi" and remaining
        else "success",
        "samples_s": samples,
        "min_s": min(samples),
        "median_s": statistics.median(samples),
        "max_s": max(samples),
        "stdev_s": statistics.stdev(samples) if len(samples) > 1 else None,
        "p95_s": statistics.quantiles(samples, n=20, method="inclusive")[18]
        if len(samples) >= 20
        else None,
        "peak_rss_kib": rss_kib,
        "python_peak_bytes": allocation_peak,
        "placed": sum(len(plan.placed_volumes) for plan in plans),
        "rejected": sum(len(plan.rejected_volumes) for plan in plans)
        if args.operation == "compare"
        else len(remaining),
        "selected_trucks": len(plans),
        "engine_calls": attempts,
        "fingerprint": fingerprint(result),
        "counts": dict(counts),
        "profile_rows": profile_rows,
    }


def _worker_command() -> list[str]:
    # Fixed executable and flags: scenario input is JSON over stdin, never CLI.
    return [sys.executable, "-m", "benchmarks.benchmark_scalability", "--worker"]


def _worker_input(args, operation, profile, count, trucks, instrument) -> str:
    return json.dumps(
        {
            "backend_root": args.backend_root,
            "operation": operation,
            "profile": profile,
            "count": count,
            "trucks": trucks,
            "iterations": args.iterations,
            "warmup": args.warmup,
            "memory_mib": args.memory_mib,
            "timeout": args.timeout,
            "instrument": instrument,
            "allocations": args.allocations,
            "experimental_limit": args.experimental_limit,
        }
    )


def _resident_peak_kib(pid: int) -> int:
    try:
        status = Path(f"/proc/{pid}/status").read_text()
    except FileNotFoundError:
        return 0
    for line in status.splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])
    return 0


def _failure_status(stderr: str, returncode: int) -> str:
    if "MemoryError" in stderr:
        return "memory_limit"
    if returncode == -24:
        return "cpu_limit"
    return "error"


def _await_worker(process, args, row, started, observation, worker_input) -> None:
    pending_input = worker_input
    while True:
        observation["rss_kib"] = max(
            observation["rss_kib"], _resident_peak_kib(process.pid)
        )
        if time.perf_counter() - started >= args.timeout:
            process.kill()
            process.communicate()
            row.update(status="timeout", timeout_s=args.timeout)
            return
        try:
            stdout, stderr = process.communicate(input=pending_input, timeout=0.1)
        except subprocess.TimeoutExpired:
            pending_input = None
            continue
        if process.returncode == 0:
            row.update(json.loads(stdout))
        else:
            row.update(
                status=_failure_status(stderr, process.returncode),
                returncode=process.returncode,
                error=stderr[-3000:],
            )
        return


def run_case(args, operation, profile, count, trucks, *, instrument=False):
    command = _worker_command()
    payload = _worker_input(args, operation, profile, count, trucks, instrument)
    row = {
        "operation": operation,
        "profile": profile,
        "volumes": count,
        "trucks": trucks,
        "instrumented": instrument,
    }
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    observation = {"rss_kib": 0}
    try:
        _await_worker(process, args, row, started, observation, payload)
    except KeyboardInterrupt:
        process.kill()
        process.communicate()
        row.update(
            status="interrupted",
            process_elapsed_s=time.perf_counter() - started,
            observed_process_peak_rss_kib=observation["rss_kib"],
        )
        raise _InterruptedCase(row) from None
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
    row["observed_process_peak_rss_kib"] = observation["rss_kib"]
    row["process_elapsed_s"] = time.perf_counter() - started
    return row


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-root", default=str(Path(__file__).resolve().parents[1])
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--counts", type=int, nargs="+", default=[25, 50, 100, 200])
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=[
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
        ],
    )
    parser.add_argument(
        "--operations",
        nargs="+",
        choices=["engine", "multi", "compare"],
        default=["engine", "multi", "compare"],
    )
    parser.add_argument("--truck-counts", type=int, nargs="+", default=[1, 2, 3, 5, 10])
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--memory-mib", type=int, default=768)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--experimental-limit", action="store_true")
    parser.add_argument("--instrument", action="store_true")
    parser.add_argument("--allocations", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--operation", default="engine")
    parser.add_argument("--profile", default="dense")
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--trucks", type=int, default=1)
    args = parser.parse_args()
    if (
        min(
            args.iterations,
            args.memory_mib,
            args.timeout,
            *args.counts,
            *args.truck_counts,
        )
        <= 0
        or args.warmup < 0
    ):
        parser.error(
            "positive limits/iterations/counts and non-negative warmup required"
        )

    if not args.worker and args.output is None:
        parser.error("--output is required")
    return args


def _validated_worker_args() -> argparse.Namespace:
    # Treat stdin as untrusted even when spawned by the benchmark parent.
    from benchmarks.scalability_cases import PROFILES

    values = json.load(sys.stdin)
    integers = {
        "count": (1, 1000),
        "trucks": (1, 10),
        "iterations": (1, 100),
        "warmup": (0, 20),
        "memory_mib": (64, 16384),
    }
    flags = {"instrument", "allocations", "experimental_limit"}
    strings = {"backend_root", "operation", "profile"}
    required = set(integers) | flags | strings | {"timeout"}
    if not isinstance(values, dict) or set(values) != required:
        raise ValueError("invalid benchmark worker configuration")
    for field, (minimum, maximum) in integers.items():
        value = values[field]
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"invalid worker limit: {field}")
    if type(values["timeout"]) not in (int, float) or not (
        0 < values["timeout"] <= 300
    ):
        raise ValueError("invalid worker timeout")
    if any(type(values[field]) is not bool for field in flags):
        raise ValueError("invalid worker flags")
    if values["operation"] not in ("engine", "multi", "compare"):
        raise ValueError("invalid worker operation")
    if values["profile"] not in PROFILES:
        raise ValueError("invalid worker profile")
    if not isinstance(values["backend_root"], str):
        raise TypeError("invalid worker checkout")
    values["backend_root"] = str(_resolve_backend_root(values["backend_root"]))
    if values["count"] > 200 and not values["experimental_limit"]:
        raise ValueError("oversized benchmark requires explicit experimental mode")
    return argparse.Namespace(**values)


def _run_worker_entry(_cli_args) -> None:
    import resource

    worker_args = _validated_worker_args()
    budget = worker_args.memory_mib * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (budget, budget))
    cpu_seconds = math.ceil(worker_args.timeout)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    print(json.dumps(worker(worker_args)))


def _resolve_backend_root(value: str) -> Path:
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir() or not (root / "app/modules/load_planning/optimizer").is_dir():
        raise ValueError("backend-root must point to a backend checkout")
    return root


def _git_directory(backend_root: Path) -> Path:
    marker = backend_root.parent / ".git"
    if marker.is_dir():
        return marker
    directive = marker.read_text().strip()
    if not directive.startswith("gitdir: "):
        raise ValueError("invalid worktree .git pointer")
    location = Path(directive.removeprefix("gitdir: ").strip())
    if not location.is_absolute():
        location = marker.parent / location
    return location.resolve(strict=True)


def _git_common_directory(git_dir: Path) -> Path:
    pointer = git_dir / "commondir"
    if not pointer.is_file():
        return git_dir
    location = Path(pointer.read_text().strip())
    if not location.is_absolute():
        location = git_dir / location
    return location.resolve(strict=True)


def _git_ref_value(ref: str, git_dir: Path, common_dir: Path) -> str:
    if not ref.startswith("refs/") or any(
        part in ("", ".", "..") for part in ref.split("/")
    ):
        raise ValueError("invalid symbolic Git reference")
    for directory in (git_dir, common_dir):
        loose = directory / ref
        if loose.is_file():
            return loose.read_text().strip()
        packed = directory / "packed-refs"
        if packed.is_file():
            for line in packed.read_text().splitlines():
                parts = line.split(" ", 1)
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0]
    raise ValueError("Git reference not found in checkout")


def _git_revision(backend_root: Path) -> str:
    # Read HEAD as data. Do not invoke an external command for a CLI-provided path.
    git_dir = _git_directory(backend_root)
    head = (git_dir / "HEAD").read_text().strip()
    if head.startswith("ref: "):
        ref = head.removeprefix("ref: ").strip()
        head = _git_ref_value(ref, git_dir, _git_common_directory(git_dir))
    if len(head) not in (40, 64) or any(
        digit not in "0123456789abcdefABCDEF" for digit in head
    ):
        raise ValueError("invalid Git HEAD SHA")
    return head


def _benchmark_metadata(args) -> dict:
    backend_root = _resolve_backend_root(args.backend_root)
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "cpu": next(
            (
                line.strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            None,
        ),
        "memory": [
            line
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith(("MemTotal:", "MemAvailable:"))
        ],
        "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip(),
        "cgroup_cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip(),
        "backend_revision": _git_revision(backend_root),
        "optimizer_tree_sha256": hashlib.sha256(
            b"".join(
                path.name.encode() + path.read_bytes()
                for path in sorted(
                    (backend_root / "app/modules/load_planning/optimizer").glob("*.py")
                )
            )
        ).hexdigest(),
        "case_builder_sha256": hashlib.sha256(
            Path(__file__).with_name("scalability_cases.py").read_bytes()
        ).hexdigest(),
        "method": "perf_counter; fresh process per case; ru_maxrss Linux KiB before independent oracle; profile separate from wall samples",
        "settings": {
            key: value for key, value in vars(args).items() if key != "output"
        },
        "cases": [],
    }


def _iter_cases(args):
    for operation, profile, count in product(
        args.operations, args.profiles, args.counts
    ):
        truck_counts = [1] if operation == "engine" else args.truck_counts
        for trucks in truck_counts:
            if operation == "compare" and trucks == 1:
                continue
            yield operation, profile, count, trucks


def _run_matrix(args, payload) -> None:
    for operation, profile, count, trucks in _iter_cases(args):
        interrupted = False
        try:
            row = run_case(
                args, operation, profile, count, trucks, instrument=args.instrument
            )
        except _InterruptedCase as error:
            row = error.row
            interrupted = True
        payload["cases"].append(row)
        args.output.write_text(json.dumps(payload, indent=2) + "\n")
        if interrupted:
            raise SystemExit(130)
        print(
            operation,
            profile,
            count,
            trucks,
            row["status"],
            row.get("median_s"),
            flush=True,
        )


def main() -> None:
    args = _parse_args()
    if args.worker:
        _run_worker_entry(args)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _run_matrix(args, _benchmark_metadata(args))


if __name__ == "__main__":
    main()
