"""Actual HTTP emitter, Uvicorn restart and PostgreSQL effects, without Meta."""

import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from tests.integration.test_external_commands import scenario

__all__ = ("scenario",)


def test_local_emitter_real_http_restart_and_persisted_effect(scenario, tmp_path):
    backend = Path(__file__).resolve().parents[2]
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    key = secrets.token_hex(32)
    environment = {
        **os.environ,
        "APP_ENV": "local",
        "DATABASE_URL": scenario.factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        "INBOUND_WEBHOOK_ENABLED": "true",
        "INBOUND_WEBHOOK_SIGNING_KEY": key,
        "INBOUND_WEBHOOK_BINDINGS": json.dumps(
            {"emissor-local": str(scenario.actors["manager"])}
        ),
        "INBOUND_WEBHOOK_CAPABILITIES": '["FINISH_DELIVERY","START_DELIVERY"]',
    }
    url = f"http://127.0.0.1:{port}/api/v1/webhooks/controlled-events"
    event = tmp_path / "event.json"
    before = scenario.counts()

    def emit(path, expected=200, *extra):
        result = subprocess.run(
            [
                sys.executable,
                "scripts/emit_inbound.py",
                "--url",
                url,
                "--event-file",
                str(path),
                "--expected-status",
                str(expected),
                *extra,
            ],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert key not in result.stdout + result.stderr
        return json.loads(result.stdout)

    first = None
    for restart in range(2):
        log_path = tmp_path / f"server-{restart}.log"
        with log_path.open("w") as output:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                cwd=backend,
                env=environment,
                stdout=output,
                stderr=output,
            )
            try:
                for attempt in range(100):
                    try:
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}/health", timeout=1
                        ):
                            break
                    except OSError:
                        if process.poll() is not None or attempt == 99:
                            raise
                        time.sleep(0.1)
                if restart == 0:
                    first = emit(
                        event,
                        200,
                        "--subject",
                        "emissor-local",
                        "--command",
                        "FINISH_DELIVERY",
                        "--target-id",
                        str(scenario.delivery_id),
                    )
                    assert first["duplicate"] is False
                    assert emit(event, 401, "--invalid-signature") == {
                        "http_status": 401,
                        "code": "EXTERNAL_AUTHENTICITY_INVALID",
                    }
                    assert emit(event)["duplicate"] is True
                    rejected = emit(
                        tmp_path / "wrong-state.json",
                        409,
                        "--subject",
                        "emissor-local",
                        "--command",
                        "START_DELIVERY",
                        "--target-id",
                        str(scenario.delivery_id),
                    )
                    assert rejected["http_status"] == 409
                    assert rejected["code"] == "EXTERNAL_DOMAIN_REJECTED"
                else:
                    duplicate = emit(event)
                    assert duplicate == {**first, "duplicate": True}
                assert scenario.counts() == ("DELIVERED", before[1] + 1, 1)
            finally:
                process.terminate()
                process.wait(timeout=15)
        logs = log_path.read_text()
        for sensitive in (
            key,
            "emissor-local",
            json.loads(event.read_text())["event_id"],
        ):
            assert sensitive not in logs
