"""Planning recovery must preserve the existing OC94 trip lifecycle."""

import uuid

import pytest

from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario
from tests.integration.test_oc94_exception_lifecycle import _in_route


@pytest.mark.parametrize("status", ["INTERRUPTED", "CANCELED"])
def test_continuity_accepts_oc94_status_without_creating_operations(
    client, session_factory, monkeypatch, status
):
    if status == "INTERRUPTED":
        scenario, delivery = _in_route(client, session_factory, monkeypatch)
        trip_id = delivery["trip_id"]
        action = "interruptions"
    else:
        scenario = seed_operational_scenario(session_factory)
        trip_id = create_trip(client, scenario)["id"]
        action = "cancellation"
    result = client.post(
        f"/api/v1/trips/{trip_id}/{action}",
        headers=scenario.manager_headers,
        json={
            "reason": "Reprogramacao operacional para auditoria",
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert result.status_code == 200, result.text
    endpoint = f"/api/v1/load-plans/{scenario.load_plan_id}/continuity"
    for _ in range(2):
        response = client.get(endpoint, headers=scenario.manager_headers)
        assert response.status_code == 200
        assert response.json()["trip"] == {"id": trip_id, "status": status}
    checker = client.get(endpoint, headers=scenario.checker_headers)
    assert checker.status_code == 200
    assert checker.json()["trip"] is None
    assert client.get(endpoint, headers=scenario.driver_headers).status_code == 403
