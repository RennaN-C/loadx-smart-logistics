#!/usr/bin/env python3
"""Deterministic, exhaustive CI sharding without concurrent access to a database.

Run from backend/:
  python ../.github/scripts/pytest_shards.py --verify
  python ../.github/scripts/pytest_shards.py --suite quick
  python ../.github/scripts/pytest_shards.py --suite integration --shard 0
"""

import argparse
import subprocess
import sys
from pathlib import Path

SHARDS = 4
TEST_ROOT = Path("tests")
SLOW_SUITES = {"integration", "e2e"}


def discover() -> tuple[list[Path], list[Path]]:
    """Fail closed if a new test directory is missing from the CI contract."""
    quick: list[Path] = []
    slow: list[Path] = []
    for path in sorted(TEST_ROOT.rglob("test_*.py")):
        suite = path.relative_to(TEST_ROOT).parts[0]
        if suite == "unit" or path.parent == TEST_ROOT:
            quick.append(path)
        elif suite in SLOW_SUITES:
            slow.append(path)
        else:
            raise ValueError(f"Test file has no CI suite: {path}")
    if not quick or not slow:
        raise ValueError("CI expects both quick and PostgreSQL suites")
    return quick, slow


def split_by_file(files: list[Path], count: int = SHARDS) -> list[list[Path]]:
    """Greedily balance tracked file sizes; never split a test module or its fixtures."""
    if count < 1 or len(files) < count:
        raise ValueError("Each integration shard must contain at least one test file")
    groups: list[list[Path]] = [[] for _ in range(count)]
    weights = [0] * count
    for path in sorted(files, key=lambda file: (-file.stat().st_size, file.as_posix())):
        index = min(range(count), key=lambda group: (weights[group], group))
        groups[index].append(path)
        weights[index] += path.stat().st_size
    for group in groups:
        group.sort()
    assert sorted(path for group in groups for path in group) == sorted(files)
    assert all(groups)
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("quick", "integration"))
    parser.add_argument("--shard", type=int)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    quick, integration = discover()
    groups = split_by_file(integration)
    if args.verify:
        print(f"Quick suite: {len(quick)} test files")
        for index, group in enumerate(groups):
            size = sum(path.stat().st_size for path in group)
            print(f"PostgreSQL shard {index + 1}/{SHARDS}: {len(group)} files, {size} bytes")
        print(f"All {len(quick) + len(integration)} test files assigned exactly once.")
        return 0
    if args.suite == "quick":
        if args.shard is not None:
            parser.error("--shard can only be used with --suite integration")
        selected = quick
    elif args.suite == "integration":
        if args.shard is None or not 0 <= args.shard < SHARDS:
            parser.error(f"--shard must be between 0 and {SHARDS - 1}")
        selected = groups[args.shard]
    else:
        parser.error("Provide --suite or --verify")
    print(f"Running {len(selected)} test files:", flush=True)
    for path in selected:
        print(f"  {path}", flush=True)
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *(str(path) for path in selected),
            "--cov=app",
            "--cov-report=",
            "--durations=20",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
