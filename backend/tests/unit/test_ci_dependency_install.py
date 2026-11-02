"""Exercise the CI pip command offline with synthetic dependency artifacts."""

import hashlib
import io
import os
import shlex
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def wheel(tmp_path: Path) -> Path:
    artifact = tmp_path / "ci_dependency_fixture-1.0-py3-none-any.whl"
    metadata = "ci_dependency_fixture-1.0.dist-info"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("ci_dependency_fixture.py", "VALUE = 42\n")
        archive.writestr(
            f"{metadata}/METADATA",
            "Metadata-Version: 2.1\nName: ci-dependency-fixture\nVersion: 1.0\n",
        )
        archive.writestr(
            f"{metadata}/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr(f"{metadata}/RECORD", "")
    return artifact


def run_ci_install(
    tmp_path: Path, artifact: Path, digest: str
) -> subprocess.CompletedProcess:
    workflow = Path(__file__).resolve().parents[3] / ".github/workflows/ci.yml"
    commands = [
        shlex.split(line.strip().removeprefix("run: "))
        for line in workflow.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("run: python -m pip install ")
    ]
    assert len(commands) == 1
    command = commands[0]
    command[0] = sys.executable
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        f"ci-dependency-fixture==1.0 --hash=sha256:{digest}\n", encoding="utf-8"
    )
    command[command.index("-r") + 1] = str(requirements)
    # Isolate resolution from indexes, caches, installed packages and user config.
    command.extend(
        [
            "--no-index",
            "--no-cache-dir",
            "--no-build-isolation",
            "--ignore-installed",
            "--find-links",
            str(artifact.parent),
            "--target",
            str(tmp_path / "installed"),
        ]
    )
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("PIP_")
    }
    environment["PIP_CONFIG_FILE"] = os.devnull
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=environment,
        timeout=45,
        check=False,
    )


def test_ci_installs_wheel_with_approved_hash(tmp_path: Path, wheel: Path):
    result = run_ci_install(
        tmp_path, wheel, hashlib.sha256(wheel.read_bytes()).hexdigest()
    )

    assert result.returncode == 0, result.stderr
    assert (
        tmp_path / "installed/ci_dependency_fixture.py"
    ).read_text() == "VALUE = 42\n"


def test_ci_rejects_wheel_with_unapproved_hash(tmp_path: Path, wheel: Path):
    result = run_ci_install(tmp_path, wheel, "0" * 64)

    assert result.returncode != 0
    assert "DO NOT MATCH THE HASHES" in result.stderr
    assert not (tmp_path / "installed/ci_dependency_fixture.py").exists()


def test_ci_rejects_source_distribution_before_build_code_runs(tmp_path: Path):
    marker = tmp_path / "build-executed"
    artifact = tmp_path / "ci_dependency_fixture-1.0.tar.gz"
    files = {
        "pyproject.toml": (
            '[build-system]\nrequires = []\nbuild-backend = "build_hook"\n'
            'backend-path = ["."]\n'
        ),
        "build_hook.py": (
            "from pathlib import Path\n"
            "def prepare_metadata_for_build_wheel(*args, **kwargs):\n"
            f"    Path({str(marker)!r}).write_text('executed')\n"
            "    raise RuntimeError('Source build must not run in CI')\n"
        ),
    }
    with tarfile.open(artifact, "w:gz") as archive:
        for name, content in files.items():
            data = content.encode("utf-8")
            member = tarfile.TarInfo(f"ci_dependency_fixture-1.0/{name}")
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))

    result = run_ci_install(
        tmp_path, artifact, hashlib.sha256(artifact.read_bytes()).hexdigest()
    )

    assert result.returncode != 0
    assert not marker.exists(), "CI allowed execution of source build code"
    assert "No matching distribution found" in result.stderr
