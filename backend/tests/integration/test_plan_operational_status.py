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


def test_history_partial_multi_truck_is_not_completed(client, session_factory):
    from tests.integration.oc90_helpers import seed_multi_flow

    flow = seed_multi_flow(client, session_factory)
    flow.approve()
    flow.prepare_loadings()
    for index in range(2):
        flow.finish_loading(index)
    flow.trips = [flow.create_trip(i) for i in range(2)]
    for index in range(2):
        flow.trip_status(index, "IN_ROUTE")
    flow.complete_delivery(0)
    flow.trip_status(0, "FINISHED")
    prefix = "/api/v1/load-plans"
    params = {"operation_scope": "completed", "page_size": 1}
    completed = client.get(prefix, params=params, headers=flow.headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["total"] == 0
    ongoing = client.get(
        prefix, params={"operation_scope": "ongoing"}, headers=flow.headers
    )
    assert ongoing.status_code == 200, ongoing.text
    assert ongoing.json()["total"] == 2
    for row in ongoing.json()["items"]:
        assert row["status"] == "APPROVED"
        assert row["operation"]["status"] == "PARTIALLY_DELIVERED"
        assert row["operation"]["partial_order_count"] == 1
        assert row["operation"]["delivered_order_count"] == 0
    flow.complete_delivery(1)
    # Completion of one trip is insufficient until every required order leg is delivered.
    flow.trip_status(1, "FINISHED")
    first = client.get(prefix, params=params, headers=flow.headers).json()
    second = client.get(
        prefix, params={**params, "page": 2}, headers=flow.headers
    ).json()
    assert first["total"] == second["total"] == 2
    assert len(first["items"]) == len(second["items"]) == 1
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert first["items"][0]["operation"]["status"] == "COMPLETED"
    assert first["items"][0]["operation"]["delivered_order_count"] == 1
    assert (
        client.get(
            prefix, params={"operation_scope": "ongoing"}, headers=flow.headers
        ).json()["total"]
        == 0
    )
    assert client.get(prefix, params=params, headers=flow.checker).status_code == 403
    checker = client.get(prefix, headers=flow.checker).json()
    assert all(row["operation"] is None for row in checker["items"])
    assert client.get(prefix, headers=flow.driver_headers[0]).status_code == 403


def test_history_canceled_trip_keeps_plan_state(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    trip_id = create_trip(client, scenario)["id"]
    canceled = client.post(
        f"/api/v1/trips/{trip_id}/cancellation",
        headers=scenario.manager_headers,
        json={"reason": "Reprogramação fictícia", "idempotency_key": str(uuid.uuid4())},
    )
    assert canceled.status_code == 200
    base = "/api/v1/load-plans"
    result = client.get(base, headers=scenario.manager_headers).json()
    plan = next(
        row for row in result["items"] if row["id"] == str(scenario.load_plan_id)
    )
    assert plan["status"] == "APPROVED"
    assert plan["operation"]["status"] == "CANCELED"
    for scope in ("ongoing", "completed"):
        assert (
            client.get(
                base,
                params={"operation_scope": scope},
                headers=scenario.manager_headers,
            ).json()["total"]
            == 0
        )
    assert (
        client.get(
            base,
            params={"operation_scope": "invalid"},
            headers=scenario.manager_headers,
        ).status_code
        == 422
    )
    assert client.get(base).status_code == 401


def test_calculated_plan_explains_orders_already_planned(client, session_factory):
    from tests.integration.test_load_planning_api import (
        create_authenticated_user,
        create_load_plan,
        seed_planning_scenario,
    )

    manager = create_authenticated_user(session_factory, "LOGISTICS_MANAGER")
    source = seed_planning_scenario(session_factory)
    first = create_load_plan(client, source, manager)
    second = create_load_plan(client, source, manager)
    assert first["orders_ready_for_approval"] is True
    assert (
        client.post(
            f"/api/v1/load-plans/{first['id']}/approve", headers=manager.headers
        ).status_code
        == 200
    )
    response = client.get(f"/api/v1/load-plans/{second['id']}", headers=manager.headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CALCULATED"
    assert response.json()["orders_ready_for_approval"] is False
    assert (
        client.post(
            f"/api/v1/load-plans/{second['id']}/approve", headers=manager.headers
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["loadx.trips.read", "loadx.orders.read"],
        ["loadx.trips.read", "loadx.orders.read", "loadx.loading.read"],
    ],
)
def test_operational_projection_respects_custom_effective_grants(
    client, session_factory, extra
):
    from tests.integration.auth_helpers import issue_session_headers

    scenario = seed_operational_scenario(session_factory)
    response = client.post(
        "/api/v1/access-profiles",
        headers=scenario.admin_headers,
        json={
            "name": "Consulta fictícia " + uuid.uuid4().hex,
            "permissions": ["loadx.planning.read", *extra],
        },
    )
    assert response.status_code == 201
    user = client.post(
        "/api/v1/users",
        headers=scenario.admin_headers,
        json={
            "name": "Consulta fictícia",
            "email": f"audit-{uuid.uuid4().hex}@example.test",
            "password": "Somente-teste-Local!2026",
            "role": "CUSTOM",
            "custom_profile_id": response.json()["id"],
        },
    )
    assert user.status_code == 201
    headers = issue_session_headers(session_factory, uuid.UUID(user.json()["id"]))
    allowed = len(extra) == 3
    row = client.get("/api/v1/load-plans", headers=headers).json()["items"][0]
    assert (row["operation"] is not None) is allowed
    filtered = client.get(
        "/api/v1/load-plans?operation_scope=completed", headers=headers
    )
    assert filtered.status_code == (200 if allowed else 403)
    continuity = client.get(
        f"/api/v1/load-plans/{scenario.load_plan_id}/continuity", headers=headers
    ).json()
    assert (continuity["operation"] is not None) is allowed
