"""Export measured cases and exact before/after comparisons, without imputing timeouts."""

import argparse
import csv
import json
from pathlib import Path


def _read_cases(directory: Path) -> list[dict]:
    cases = []
    for pattern in ("baseline-*.json", "optimized-*.json", "experimental-*.json"):
        for path in sorted(directory.glob(pattern)):
            cases.extend(
                {"source": path.name, **row}
                for row in json.loads(path.read_text())["cases"]
            )
    return cases


def _write_measurements(directory: Path, cases: list[dict]) -> None:
    fields = (
        "source",
        "operation",
        "profile",
        "volumes",
        "trucks",
        "instrumented",
        "status",
        "min_s",
        "median_s",
        "max_s",
        "stdev_s",
        "p95_s",
        "peak_rss_kib",
        "observed_process_peak_rss_kib",
        "placed",
        "rejected",
        "selected_trucks",
        "engine_calls",
        "timeout_s",
        "fingerprint",
    )
    with (directory / "measurements.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(cases)


def _compare_cases(cases: list[dict]) -> tuple[list[dict], list[tuple]]:
    baseline, optimized = {}, {}
    for row in cases:
        if row.get("instrumented") or "fingerprint" not in row:
            continue
        key = (row["operation"], row["profile"], row["volumes"], row["trucks"])
        if row["source"].startswith("baseline-"):
            baseline.setdefault(key, row)
        elif row["source"].startswith("optimized-"):
            optimized.setdefault(key, row)
    mismatches = []
    comparisons = []
    for key in sorted(baseline.keys() & optimized.keys()):
        before, after = baseline[key], optimized[key]
        equivalent = before["fingerprint"] == after["fingerprint"]
        if not equivalent:
            mismatches.append(key)
        comparisons.append(
            {
                "operation": key[0],
                "profile": key[1],
                "volumes": key[2],
                "trucks": key[3],
                "equivalent": equivalent,
                "baseline_source": before["source"],
                "optimized_source": after["source"],
                "before_s": before["median_s"],
                "after_s": after["median_s"],
                "ratio": before["median_s"] / after["median_s"],
            }
        )
    return comparisons, mismatches


def summarize(directory: Path) -> dict:
    cases = _read_cases(directory)
    _write_measurements(directory, cases)
    comparisons, mismatches = _compare_cases(cases)
    result = {
        "compared_complete_outputs": len(comparisons),
        "mismatches": mismatches,
        "comparisons": comparisons,
        "note": "Instrumented rounds excluded. Ratios of separate manual rounds are descriptive, not SLO or CI thresholds. Censored cases are never imputed.",
    }
    (directory / "comparison-summary.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = summarize(args.directory)
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "comparisons"},
            indent=2,
        )
    )
    if result["mismatches"]:
        raise SystemExit("physical output mismatch: do not publish")


if __name__ == "__main__":
    main()
