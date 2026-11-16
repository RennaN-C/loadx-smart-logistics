"""Runner failure paths stay bounded and cannot silently count as success."""

import argparse
import json
import sys
from io import StringIO
from pathlib import Path
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


def test_git_revision_reads_metadata_without_executing_git(tmp_path, monkeypatch):
    backend = tmp_path / "checkout --upload-pack=unsafe" / "backend"
    (backend / "app/modules/load_planning/optimizer").mkdir(parents=True)
    git_dir = backend.parent / ".git"
    (git_dir / "refs/heads").mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/test\n")
    (git_dir / "refs/heads/test").write_text("a" * 40 + "\n")
    check_output = Mock()
    monkeypatch.setattr(runner.subprocess, "check_output", check_output)
    resolved = runner._resolve_backend_root(str(backend))
    assert runner._git_revision(resolved) == "a" * 40
    check_output.assert_not_called()


def test_git_revision_resolves_packed_worktree_refs(tmp_path):
    backend = tmp_path / "checkout" / "backend"
    (backend / "app/modules/load_planning/optimizer").mkdir(parents=True)
    common_dir = tmp_path / "metadata"
    git_dir = common_dir / "worktrees/benchmark"
    git_dir.mkdir(parents=True)
    (backend.parent / ".git").write_text(f"gitdir: {git_dir}\n")
    (git_dir / "HEAD").write_text("ref: refs/heads/benchmark\n")
    (git_dir / "commondir").write_text("../..\n")
    (common_dir / "packed-refs").write_text("b" * 40 + " refs/heads/benchmark\n")
    assert runner._git_revision(backend) == "b" * 40


def test_worker_receives_configuration_only_as_json_stdin(monkeypatch):
    process = Mock(pid=999999999, returncode=0)
    process.poll.return_value = 0
    process.communicate.return_value = '{"status": "success"}', ""
    popen = Mock(return_value=process)
    monkeypatch.setattr(runner.subprocess, "Popen", popen)
    args = arguments(backend_root="--upload-pack=unsafe")
    result = runner.run_case(args, "engine", "dense", 25, 1)
    assert result["status"] == "success"
    assert popen.call_args.args[0] == [
        runner.sys.executable,
        "-m",
        "benchmarks.benchmark_scalability",
        "--worker",
    ]
    payload = json.loads(process.communicate.call_args.kwargs["input"])
    assert payload["backend_root"] == "--upload-pack=unsafe"


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("count", 1001),
        ("memory_mib", -1),
        ("timeout", float("inf")),
        ("operation", "--unsafe"),
        ("experimental_limit", "true"),
        ("backend_root", 123),
    ],
)
def test_worker_rejects_untrusted_json_payload(tmp_path, monkeypatch, field, bad_value):
    backend = tmp_path / "backend"
    (backend / "app/modules/load_planning/optimizer").mkdir(parents=True)
    payload = {
        "backend_root": str(backend),
        "operation": "engine",
        "profile": "dense",
        "count": 1,
        "trucks": 1,
        "iterations": 1,
        "warmup": 0,
        "memory_mib": 768,
        "timeout": 30,
        "instrument": False,
        "allocations": False,
        "experimental_limit": False,
    }
    payload[field] = bad_value
    monkeypatch.setattr(runner.sys, "stdin", StringIO(json.dumps(payload)))
    expected = TypeError if field == "backend_root" else ValueError
    with pytest.raises(expected):
        runner._validated_worker_args()


@pytest.mark.parametrize(
    "filename",
    ["../../etc/passwd.json", "/tmp/unsafe.json", "subdir/result.json", "bad;name.json"],
)
def test_output_rejects_untrusted_paths(filename):
    with pytest.raises(ValueError):
        runner._safe_output_name(Path(filename))


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux safe file handles")
def test_private_output_writes_json_without_arbitrary_path(tmp_path, monkeypatch):
    output_dir = tmp_path / "private-benchmarks"
    monkeypatch.setattr(runner, "_OUTPUT_DIRECTORY", output_dir)
    filename = runner._safe_output_name(Path("baseline-engine.json"))
    runner._write_benchmark_json(filename, {"cases": [{"status": "success"}]})
    saved = json.loads((output_dir / filename).read_text())
    assert saved == {"cases": [{"status": "success"}]}
    assert output_dir.stat().st_mode & 0o777 == 0o700


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux O_NOFOLLOW")
def test_private_output_refuses_symlink_overwrite(tmp_path, monkeypatch):
    output_dir = tmp_path / "private-benchmarks"
    output_dir.mkdir(mode=0o700)
    monkeypatch.setattr(runner, "_OUTPUT_DIRECTORY", output_dir)
    victim = tmp_path / "victim.json"
    victim.write_text("protected")
    (output_dir / "baseline-engine.json").symlink_to(victim)
    with pytest.raises(OSError):
        runner._write_benchmark_json("baseline-engine.json", {"data": "malicious"})
    assert victim.read_text() == "protected"


@pytest.mark.skipif(sys.platform != "linux", reason="worker uses Linux resource limits")
def test_real_worker_json_round_trip_runs_small_engine():
    backend_root = Path(__file__).resolve().parents[3]
    args = arguments(backend_root=str(backend_root), memory_mib=768, timeout=30)
    result = runner.run_case(args, "engine", "dense", 1, 1)
    assert result["status"] == "success"
    assert result["placed"] == 1
    assert result["rejected"] == 0
    assert result["fingerprint"]


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
