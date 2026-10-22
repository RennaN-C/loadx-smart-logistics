"""Real PostgreSQL contract checks for OC96 summary and exports."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from io import StringIO
import csv

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_deliveries_api import seed_operational_scenario

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
        "trips_created", "trips_started", "trips_finished",
        "deliveries_completed", "orders_with_completed_leg",
        "occurrences_registered", "delivery_exceptions", "trips_canceled",
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
