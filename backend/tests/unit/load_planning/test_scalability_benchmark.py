"""Runner failure paths stay bounded and cannot silently count as success."""

import argparse
from unittest.mock import Mock

import pytest

from benchmarks import benchmark_scalability as runner
from benchmarks.scalability_cases import build_case


def arguments(**changes):
    values = {
        "backend_root": "backend",
        "iterations": 1,
        "warmup": 0,
        "memory_mib": 64,
        "experimental_limit": False,
        "allocations": False,
        "timeout": 1,
    }
    values.update(changes)
    return argparse.Namespace(**values)


def test_timeout_kills_and_reaps_worker_and_is_not_a_success(monkeypatch):
    process = Mock(pid=999999999)
    process.poll.return_value = -9
    monkeypatch.setattr(runner.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(runner.time, "perf_counter", Mock(side_effect=(0, 2, 2)))
    result = runner.run_case(arguments(), "engine", "dense", 25, 1)
    assert result["status"] == "timeout"
    assert "samples_s" not in result
    process.kill.assert_called_once()
    process.communicate.assert_called_once()


@pytest.mark.parametrize(
    "stderr,code,status",
    [
        ("MemoryError", 1, "memory_limit"),
        ("domain failure", 1, "error"),
        ("", -24, "cpu_limit"),
    ],
)
def test_worker_failure_is_preserved(monkeypatch, stderr, code, status):
    process = Mock(pid=999999999, returncode=code)
    process.poll.return_value = code
    process.communicate.return_value = "", stderr
    monkeypatch.setattr(runner.subprocess, "Popen", Mock(return_value=process))
    result = runner.run_case(arguments(), "engine", "dense", 25, 1)
    assert result["status"] == status
    assert result["error"] == stderr


def test_interruption_kills_worker_and_propagates(monkeypatch):
    process = Mock(pid=999999999)
    process.poll.return_value = -9
    process.communicate.side_effect = (KeyboardInterrupt, ("", ""))
    monkeypatch.setattr(runner.subprocess, "Popen", Mock(return_value=process))
    args = arguments()
    with pytest.raises(runner._InterruptedCase) as error:
        runner.run_case(args, "engine", "dense", 25, 1)
    assert error.value.row["status"] == "interrupted"
    process.kill.assert_called_once()
    assert process.communicate.call_count == 2


def test_git_revision_never_interprets_backend_root_as_git_cli_option(
    tmp_path, monkeypatch
):
    backend = tmp_path / "checkout --upload-pack=unsafe" / "backend"
    (backend / "app/modules/load_planning/optimizer").mkdir(parents=True)
    check_output = Mock(return_value="abcdef123456\n")
    monkeypatch.setattr(runner.subprocess, "check_output", check_output)
    resolved = runner._resolve_backend_root(str(backend))
    assert runner._git_revision(resolved) == "abcdef123456"
    check_output.assert_called_once_with(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=resolved, text=True
    )


@pytest.mark.parametrize("count", [25, 50, 100, 200, 500, 1000])
def test_dense_profile_can_fit_every_volume_without_weight_rejections(count):
    case = build_case("dense", count, 1)
    truck = case.trucks[0]
    assert sum(item.quantity for item in case.items) == count
    slots = (
        (truck.internal_width_cm // 10)
        * (truck.internal_height_cm // 10)
        * (truck.internal_length_cm // 10)
    )
    assert slots >= count
    assert (
        sum(item.weight_kg * item.quantity for item in case.items)
        <= truck.max_weight_kg
    )
