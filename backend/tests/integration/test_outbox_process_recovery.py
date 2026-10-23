"""New OC84 events: actual PostgreSQL and fresh OS workers, no external sends."""

import json
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.integrations.outbox import DeliveryEnvelope
from app.modules.notifications.outbox_models import (
    OutboxAttempt,
    OutboxEvent,
    OutboxRetryCommand,
)
from app.modules.notifications.outbox_repository import OutboxRepository
from app.modules.notifications.outbox_service import Claim, OutboxService
from app.modules.status_history.models import AuditEvent
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_external_commands import scenario
from tests.integration.test_outbox import due, queued, session_factory, snapshot

__all__ = ("queued", "scenario", "session_factory")
ROOT = Path(__file__).resolve().parents[2]


def launch(s, mode, *barrier):
    with s.factory() as db:
        url = db.bind.url.render_as_string(hide_password=False)
    environment = {**os.environ, "OUTBOX_TEST_DATABASE_URL": url, "APP_ENV": "local"}
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "tests.integration.outbox_process_probe",
            mode,
            *map(str, barrier),
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def result(process, expected=0):
    try:
        stdout, _stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        pytest.fail("Isolated outbox probe timed out")
    assert process.returncode == expected, (
        "Outbox subprocess failed; no raw payload logged"
    )
    return json.loads(stdout) if expected == 0 else None


def run(s, mode):
    return result(launch(s, mode))


def attempts(s, identifier):
    with s.factory() as db:
        rows = list(
            db.scalars(
                select(OutboxAttempt)
                .where(OutboxAttempt.outbox_event_id == identifier)
                .order_by(OutboxAttempt.generation)
            )
        )
        return [
            (row.generation, row.origin, row.result, row.error_code) for row in rows
        ]


def admin_retry(client, s, identifier, command):
    return client.post(
        f"/api/v1/outbox-events/{identifier}/retry",
        json={"command_id": str(command)},
        headers=issue_session_headers(s.factory, s.actors["admin"]),
    )


def test_new_event_transient_backoff_is_durable_across_fresh_processes(queued):
    s, identifier, _ = queued
    assert snapshot(s, identifier)[:3] == ("PENDING", 0, 0)
    for generation, bounds in [(1, (15, 30)), (2, (20, 40)), (3, (20, 40))]:
        if generation > 1:
            due(s, identifier)  # explicit isolated clock boundary; do not sleep 30s.
        assert run(s, "transient") == {"progressed": True, "calls": 1}
        assert snapshot(s, identifier) == (
            "RETRYABLE",
            generation,
            generation,
            "TRANSIENT",
        )
        with s.factory() as db:
            row = db.get(OutboxEvent, identifier)
            delay = (row.next_attempt_at - row.updated_at).total_seconds()
            assert bounds[0] <= delay <= bounds[1]
        assert run(s, "mock") == {"progressed": False, "calls": 0}
        assert len(attempts(s, identifier)) == generation
    due(s, identifier)
    assert run(s, "mock") == {"progressed": True, "calls": 1}
    assert snapshot(s, identifier) == ("SUCCEEDED", 4, 4, None)
    assert run(s, "mock") == {"progressed": False, "calls": 0}
    assert [a[1] for a in attempts(s, identifier)] == ["WORKER"] * 4


def test_process_crash_lease_recovery_admin_retry_and_stale_result_fencing(
    client, queued
):
    s, identifier, _ = queued
    result(launch(s, "crash"), expected=73)
    assert snapshot(s, identifier)[:3] == ("PROCESSING", 1, 1)
    assert run(s, "mock") == {"progressed": False, "calls": 0}
    with s.factory() as db, db.begin():
        row = db.get(OutboxEvent, identifier)
        row.lease_expires_at = OutboxRepository(db).now() - timedelta(seconds=1)
    assert run(s, "mock") == {"progressed": False, "calls": 0}
    assert snapshot(s, identifier) == ("UNCERTAIN", 1, 1, "LEASE_EXPIRED")
    command = uuid.uuid4()
    first = admin_retry(client, s, identifier, command)
    second = admin_retry(client, s, identifier, command)
    assert first.status_code == second.status_code == 200
    assert snapshot(s, identifier)[:3] == ("PENDING", 0, 1)
    assert run(s, "mock") == {"progressed": True, "calls": 1}
    old = Claim(identifier, 1, DeliveryEnvelope("", "", ""))
    with s.factory() as db, db.begin():
        assert not OutboxService(db).complete(
            old, "SUCCEEDED", None, max_attempts=5, base_seconds=30, cap_seconds=40
        )
    assert snapshot(s, identifier) == ("SUCCEEDED", 1, 2, None)
    assert attempts(s, identifier) == [
        (1, "WORKER", "UNCERTAIN", "LEASE_EXPIRED"),
        (2, "WORKER", "SUCCEEDED", None),
    ]
    with s.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(OutboxRetryCommand)
                .where(OutboxRetryCommand.outbox_event_id == identifier)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.entity_id == identifier,
                    AuditEvent.event_type == "OUTBOX_REPROCESSED",
                )
            )
            == 1
        )


@pytest.mark.parametrize("retryable", [False, True])
def test_two_os_workers_dispute_one_new_event_without_duplicate_attempt(
    queued, tmp_path, retryable
):
    s, identifier, _ = queued
    if retryable:
        assert run(s, "transient")["calls"] == 1
        due(s, identifier)
    start = tmp_path / "start"
    ready = [tmp_path / f"worker-{i}" for i in range(2)]
    processes = [launch(s, "mock", path, start) for path in ready]
    try:
        deadline = time.monotonic() + 20
        while not all(path.exists() for path in ready):
            assert time.monotonic() < deadline, "Worker startup barrier exceeded"
            time.sleep(0.01)
        start.touch()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(result, processes))
        assert sorted(item["calls"] for item in outcomes) == [0, 1]
        assert sorted(item["progressed"] for item in outcomes) == [False, True]
        expected = 2 if retryable else 1
        assert snapshot(s, identifier) == ("SUCCEEDED", expected, expected, None)
        assert len(attempts(s, identifier)) == expected
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()


def test_unknown_timeout_never_retries_automatically_and_api_is_sanitized(
    client, queued
):
    s, identifier, _ = queued
    assert run(s, "timeout") == {"progressed": True, "calls": 1}
    assert snapshot(s, identifier) == ("UNCERTAIN", 1, 1, "TIMEOUT_UNKNOWN")
    assert run(s, "mock") == {"progressed": False, "calls": 0}
    headers = issue_session_headers(s.factory, s.actors["admin"])
    response = client.get(
        f"/api/v1/outbox-events/{identifier}/attempts", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["error_code"] == "TIMEOUT_UNKNOWN"
    assert "fixture-only-sensitive-marker" not in response.text
    command = uuid.uuid4()
    assert admin_retry(client, s, identifier, command).status_code == 200
    assert run(s, "mock") == {"progressed": True, "calls": 1}
    replay = admin_retry(client, s, identifier, command)
    assert replay.status_code == 200
    assert replay.json()["status"] == "SUCCEEDED"
    assert run(s, "mock") == {"progressed": False, "calls": 0}
