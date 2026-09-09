from fastapi.testclient import TestClient

from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario
from tests.integration.test_messages_api import finish_loading


def assert_pdf_download(response, filename_prefix: str) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith(
        f'attachment; filename="{filename_prefix}'
    )
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 1_000


def test_downloads_loading_and_trip_reports(
    client: TestClient,
    session_factory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    finish_loading(client, scenario)
    occurrence = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": trip["id"],
            "delivery_id": trip["deliveries"][0]["id"],
            "type": "DELAY",
            "description": "Atraso controlado para o relatório.",
            "photo_url": "mock://occurrences/report-photo",
        },
        headers=scenario.manager_headers,
    )
    assert occurrence.status_code == 201

    loading_report = client.get(
        f"/api/v1/reports/load-plans/{scenario.load_plan_id}",
        headers=scenario.manager_headers,
    )
    trip_report = client.get(
        f"/api/v1/reports/trips/{trip['id']}",
        headers=scenario.manager_headers,
    )

    assert_pdf_download(loading_report, "loading-report-")
    assert_pdf_download(trip_report, "trip-report-")


def test_reports_require_authorization_and_existing_sources(
    client: TestClient,
    session_factory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)

    forbidden = client.get(
        f"/api/v1/reports/trips/{trip['id']}",
        headers=scenario.driver_headers,
    )
    missing_loading = client.get(
        f"/api/v1/reports/load-plans/{scenario.load_plan_id}",
        headers=scenario.manager_headers,
    )

    assert forbidden.status_code == 403
    assert missing_loading.status_code == 404
    assert missing_loading.json()["code"] == "LOADING_SESSION_NOT_FOUND"
