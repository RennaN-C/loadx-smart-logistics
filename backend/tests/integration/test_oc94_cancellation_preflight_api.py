"""Real PostgreSQL-backed cancellation eligibility and authorization tests."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_deliveries_api import (
    create_trip,
    seed_operational_scenario,
)

SessionFactory = Callable[[], Session]


def test_oc94_preflight_rejects_unapproved_roles_and_leaves_state_unchanged(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    uri = f"/api/v1/trips/{trip['id']}/cancellation-preflight"

    response = client.get(uri, headers=scenario.manager_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["trip_id"] == trip["id"]
    assert data["safe_for_cancellation_workflow"] is True
    assert data["blocking_reasons"] == []
    assert data["next_action"] == "PREPARAR_RECONCILIACAO_TRANSACIONAL"

    assert client.get(uri, headers=scenario.admin_headers).status_code == 200
    assert client.get(uri, headers=scenario.driver_headers).status_code == 403
    assert client.get(uri, headers=scenario.checker_headers).status_code == 403
    assert client.get(uri).status_code == 401
    assert (
        client.get(
            f"/api/v1/trips/{uuid.uuid4()}/cancellation-preflight",
            headers=scenario.manager_headers,
        ).status_code
        == 404
    )
    persisted = client.get(
        f"/api/v1/trips/{trip['id']}", headers=scenario.manager_headers
    )
    assert persisted.status_code == 200
    assert persisted.json()["status"] == "SCHEDULED"


def test_oc94_preflight_blocks_even_pending_loading_session(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    loading = client.post(
        "/api/v1/loading-sessions",
        json={"load_plan_id": str(scenario.load_plan_id)},
        headers=scenario.manager_headers,
    )
    assert loading.status_code == 201
    assert loading.json()["status"] == "PENDING"

    uri = f"/api/v1/trips/{trip['id']}/cancellation-preflight"
    result = client.get(uri, headers=scenario.manager_headers)
    assert result.status_code == 200
    assert result.json()["safe_for_cancellation_workflow"] is False
    assert "LOADING_SESSION_EXISTS" in result.json()["blocking_reasons"]
    # GET must not release the reservation or mutate the loading session.
    unchanged = client.get(
        f"/api/v1/loading-sessions/{loading.json()['id']}",
        headers=scenario.checker_headers,
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["status"] == "PENDING"
