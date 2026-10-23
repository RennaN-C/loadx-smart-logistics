"""Agenda read-only real PostgreSQL and effective RBAC."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_deliveries_api import (
    create_trip,
    seed_operational_scenario,
)

SessionFactory = Callable[[], Session]


def test_operational_agenda_respects_driver_scope_and_time_window(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    now = datetime.now(UTC)
    params = {
        "start": (now - timedelta(days=1)).isoformat(),
        "end": (now + timedelta(days=1)).isoformat(),
    }
    path = "/api/v1/operations/agenda"
    assert client.get(path, params=params).status_code == 401
    assert (
        client.get(path, params=params, headers=scenario.checker_headers).status_code
        == 403
    )

    for headers in (scenario.manager_headers, scenario.driver_headers):
        response = client.get(path, params=params, headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1
        assert any(
            event["kind"] == "TRIP_CREATED" and event["trip_id"] == trip["id"]
            for event in body["items"]
        )
        assert all(
            "reason" not in event and "description" not in event
            for event in body["items"]
        )

    other = client.get(path, params=params, headers=scenario.other_driver_headers)
    assert other.status_code == 200
    assert other.json()["items"] == []

    invalid = client.get(
        path, params={**params, "kind": "INVALID"}, headers=scenario.manager_headers
    )
    assert invalid.status_code == 422


def test_operational_agenda_refuses_period_over_seven_days(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    now = datetime.now(UTC)
    response = client.get(
        "/api/v1/operations/agenda",
        params={
            "start": (now - timedelta(days=9)).isoformat(),
            "end": now.isoformat(),
        },
        headers=scenario.manager_headers,
    )
    assert response.status_code == 422


def test_agenda_cancellation_filter_preserves_driver_isolation_and_replay(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    command = {
        "reason": "Reprogramacao operacional aprovada",
        "idempotency_key": str(uuid.uuid4()),
    }
    for _ in range(2):
        canceled = client.post(
            f"/api/v1/trips/{trip['id']}/cancellation",
            json=command,
            headers=scenario.manager_headers,
        )
        assert canceled.status_code == 200, canceled.text
    now = datetime.now(UTC)
    params = {
        "start": (now - timedelta(days=1)).isoformat(),
        "end": (now + timedelta(days=1)).isoformat(),
        "kind": "TRIP_CANCELED",
        "driver_id": trip["driver_id"],
    }
    uri = "/api/v1/operations/agenda"
    for headers in (scenario.manager_headers, scenario.driver_headers):
        response = client.get(uri, params=params, headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["trip_id"] == trip["id"]
        assert response.json()["items"][0]["kind"] == "TRIP_CANCELED"
    assert (
        client.get(
            uri, params=params, headers=scenario.other_driver_headers
        ).status_code
        == 403
    )
    empty = client.get(
        uri,
        params={**params, "driver_id": str(uuid.uuid4())},
        headers=scenario.manager_headers,
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
