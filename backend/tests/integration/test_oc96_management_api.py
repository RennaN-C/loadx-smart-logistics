"""Real PostgreSQL contract checks for OC96 summary and exports."""

import csv
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from io import StringIO

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_deliveries_api import (
    create_trip,
    seed_operational_scenario,
)

SessionFactory = Callable[[], Session]


def test_management_summary_csv_pdf_share_real_counts_and_enforce_rbac(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    params = {
        "start": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        "end": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }
    endpoint = "/api/v1/reports/management-summary"
    unauthorized = client.get(endpoint, params=params)
    assert unauthorized.status_code == 401
    forbidden = client.get(endpoint, params=params, headers=scenario.driver_headers)
    assert forbidden.status_code == 403

    response = client.get(endpoint, params=params, headers=scenario.manager_headers)
    assert response.status_code == 200
    result = response.json()
    for key in (
        "trips_created",
        "trips_started",
        "trips_finished",
        "deliveries_completed",
        "orders_with_completed_leg",
        "occurrences_registered",
        "delivery_exceptions",
        "trips_canceled",
        "interruption_events",
    ):
        assert key in result
        assert isinstance(result[key], int)
        assert result[key] >= 0

    csv_response = client.get(
        endpoint + ".csv", params=params, headers=scenario.manager_headers
    )
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(StringIO(csv_response.text)))
    assert rows[0] == ["Indicador", "Total"]
    assert len(rows) == 10

    pdf_response = client.get(
        endpoint + ".pdf", params=params, headers=scenario.manager_headers
    )
    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF")


def test_oc96_rejects_unbounded_or_naive_period(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    now = datetime.now(UTC)
    url = "/api/v1/reports/management-summary"
    for params in (
        {
            "start": (now - timedelta(days=100)).isoformat(),
            "end": now.isoformat(),
        },
        {
            "start": now.replace(tzinfo=None).isoformat(),
            "end": (now + timedelta(days=1)).isoformat(),
        },
    ):
        response = client.get(url, params=params, headers=scenario.manager_headers)
        assert response.status_code == 422


def test_management_counts_cancellation_once_and_scopes_driver(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    command = {
        "reason": "Reprogramacao operacional confirmada",
        "idempotency_key": str(uuid.uuid4()),
    }
    for _ in range(2):
        result = client.post(
            f"/api/v1/trips/{trip['id']}/cancellation",
            headers=scenario.manager_headers,
            json=command,
        )
        assert result.status_code == 200, result.text
    params = {
        "start": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        "end": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "driver_id": trip["driver_id"],
    }
    endpoint = "/api/v1/reports/management-summary"
    response = client.get(endpoint, params=params, headers=scenario.manager_headers)
    assert response.status_code == 200
    assert response.json()["trips_created"] == 1
    assert response.json()["trips_canceled"] == 1
    assert response.json()["deliveries_completed"] == 0
    exported = client.get(
        endpoint + ".csv", params=params, headers=scenario.manager_headers
    )
    assert exported.status_code == 200
    rows = list(csv.reader(StringIO(exported.text)))
    assert ["Viagens canceladas", "1"] in rows
    unrelated = client.get(
        endpoint,
        params={**params, "driver_id": str(uuid.uuid4())},
        headers=scenario.manager_headers,
    )
    assert unrelated.status_code == 200
    assert unrelated.json()["trips_created"] == 0
    assert unrelated.json()["trips_canceled"] == 0
