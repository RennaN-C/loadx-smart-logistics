"""Durability across actual API process restart, with PostgreSQL and mock only."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import delete

from app.modules.auth.models import AuthSession
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_durable_notifications import counts, row_for
from tests.integration.test_external_commands import scenario

__all__ = ("scenario",)


@contextmanager
def running_server(s, port, log):
    environment = {
        **os.environ,
        "APP_ENV": "local",
        "DATABASE_URL": s.factory.kw["bind"].url.render_as_string(hide_password=False),
    }
    with log.open("w") as output:
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
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            stdout=output,
            stderr=output,
        )
        try:
            for attempt in range(100):
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/ready", timeout=1
                    ):
                        break
                except OSError:
                    if process.poll() is not None or attempt == 99:
                        raise
                    time.sleep(0.1)
            yield
        finally:
            process.terminate()
            process.wait(timeout=15)


def test_real_http_restart_preserves_notification_and_get_has_no_effect(
    scenario, tmp_path
):
    s = scenario
    headers = {
        **issue_session_headers(s.factory, s.actors["manager"]),
        "Origin": "http://localhost:5173",
        "Content-Type": "application/json",
    }
    with socket.socket() as address:
        address.bind(("127.0.0.1", 0))
        port = address.getsockname()[1]
    try:
        with running_server(s, port, tmp_path / "server-first.log"):
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/v1/occurrences",
                data=json.dumps(
                    {
                        "trip_id": str(s.trip_id),
                        "type": "DELAY",
                        "description": "Fato fictício entre processos.",
                    }
                ).encode(),
                headers=headers,
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                assert response.status == 201
                occurrence_id = uuid.UUID(json.load(response)["id"])
            row = row_for(s, occurrence_id)
            notification_id = row.id
            assert row.mock_status == "SIMULATED"
        with running_server(s, port, tmp_path / "server-restarted.log"):
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/v1/trips/{s.trip_id}/occurrences",
                headers=headers,
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                assert json.load(response)[0]["id"] == str(occurrence_id)
            row = row_for(s, occurrence_id)
            assert row.id == notification_id
            assert row.mock_status == "SIMULATED"
            assert counts(s) == (1, 1)
    finally:
        with s.factory() as db:
            db.execute(
                delete(AuthSession).where(AuthSession.user_id == s.actors["manager"])
            )
            db.commit()
