"""PostgreSQL-backed RBAC/pagination regressions for OC93 operational lists."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_deliveries_api import (
    create_trip,
    seed_operational_scenario,
)

SessionFactory = Callable[[], Session]


def test_loading_discovery_reuses_existing_records_and_permission_boundary(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    created = client.post(
        "/api/v1/loading-sessions",
        json={"load_plan_id": str(scenario.load_plan_id)},
        headers=scenario.manager_headers,
    )
    assert created.status_code == 201
    loading_id = created.json()["id"]

    for headers in (
        scenario.manager_headers,
        scenario.admin_headers,
        scenario.checker_headers,
    ):
        response = client.get(
            "/api/v1/loading-sessions?page=1&page_size=1&status=PENDING",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == loading_id
        assert response.json()["total"] == 1
        assert response.json()["page_size"] == 1

    forbidden = client.get("/api/v1/loading-sessions", headers=scenario.driver_headers)
    assert forbidden.status_code == 403
    assert client.get("/api/v1/loading-sessions").status_code == 401
    assert (
        client.get(
            "/api/v1/loading-sessions?status=UNSUPPORTED",
            headers=scenario.manager_headers,
        ).status_code
        == 422
    )


def test_delivery_discovery_isolated_by_driver_and_filter(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    trip_id = trip["id"]

    manager = client.get(
        "/api/v1/deliveries?page=1&page_size=1&status=PENDING",
        headers=scenario.manager_headers,
    )
    assert manager.status_code == 200
    assert manager.json()["total"] == 2
    assert len(manager.json()["items"]) == 1
    assert manager.json()["items"][0]["trip_id"] == trip_id

    own = client.get("/api/v1/deliveries", headers=scenario.driver_headers)
    assert own.status_code == 200
    assert own.json()["total"] == 2
    assert {item["trip_id"] for item in own.json()["items"]} == {trip_id}

    stranger = client.get("/api/v1/deliveries", headers=scenario.other_driver_headers)
    assert stranger.status_code == 200
    assert stranger.json()["total"] == 0
    assert stranger.json()["items"] == []

    checker = client.get("/api/v1/deliveries", headers=scenario.checker_headers)
    assert checker.status_code == 403
    assert client.get("/api/v1/deliveries").status_code == 401
    assert (
        client.get(
            "/api/v1/deliveries?status=INVALID",
            headers=scenario.manager_headers,
        ).status_code
        == 422
    )


def test_oc93_filters_trip_status_and_accepts_canceled_delivery_state(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    response = client.get(
        "/api/v1/trips?status=SCHEDULED",
        headers=scenario.manager_headers,
    )
    assert response.status_code == 200
    assert any(row["id"] == trip["id"] for row in response.json()["items"])
    invalid = client.get(
        "/api/v1/trips?status=INVALID", headers=scenario.manager_headers
    )
    assert invalid.status_code == 422
    canceled = client.get(
        "/api/v1/deliveries?status=CANCELED",
        headers=scenario.manager_headers,
    )
    assert canceled.status_code == 200
    assert canceled.json()["items"] == []
