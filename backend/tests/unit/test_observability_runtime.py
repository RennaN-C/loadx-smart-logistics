"""Exercise the production server logging path, beyond TestClient capture."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def test_uvicorn_failure_logs_omit_secrets_and_correlate(tmp_path):
    backend_root = Path(__file__).resolve().parents[2]
    helper = tmp_path / "runtime_app.py"
    helper.write_text(
        "from app.main import create_app\n"
        "app = create_app()\n"
        "@app.get('/failure/{value}')\n"
        "def failure(value: str):\n"
        "    raise RuntimeError('runtime-provider-secret')\n"
    )
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    environment = {
        **os.environ,
        "APP_ENV": "local",
        "OPERATIONAL_LOG_LEVEL": "INFO",
        "OPERATIONAL_REQUEST_LOGS": "true",
        "PYTHONPATH": str(backend_root),
    }
    log_path = tmp_path / "runtime.log"
    with log_path.open("w") as output:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "runtime_app:app",
                "--app-dir",
                str(tmp_path),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            cwd=backend_root,
            env=environment,
            stdout=output,
            stderr=output,
        )
        try:
            for attempt in range(50):
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/health", timeout=1
                    ):
                        break
                except OSError:
                    if attempt == 49 or process.poll() is not None:
                        raise
                    time.sleep(0.1)
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/failure/runtime-private-person?token=runtime-query-secret",
                headers={"Authorization": "Bearer runtime-auth-secret"},
            )
            try:
                urllib.request.urlopen(request, timeout=5)
            except urllib.error.HTTPError as response:
                assert response.code == 500
                request_id = response.headers["X-Request-ID"]
            else:
                raise AssertionError("expected controlled 500 response")
        finally:
            process.terminate()
            process.wait(timeout=10)
    logs = log_path.read_text()
    for marker in (
        "runtime-provider-secret",
        "runtime-private-person",
        "runtime-query-secret",
        "runtime-auth-secret",
    ):
        assert marker not in logs
    assert "Traceback" not in logs
    events = [
        json.loads(line) for line in logs.splitlines() if line.startswith('{"event"')
    ]
    failures = [event for event in events if event["event"] == "HTTP_REQUEST_FAILED"]
    assert len(failures) == 1
    assert failures[0]["request_id"] == request_id
    assert failures[0]["exception_type"] == "RuntimeError"
    assert failures[0]["route"] == "/failure/{value}"
    assert any(event["event"] == "APP_STOPPED" for event in events)
