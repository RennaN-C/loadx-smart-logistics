"""Loading lookups outside the loading router must keep the same tenant scope."""

from datetime import UTC, datetime, timedelta

from app.modules.deliveries.models import Trip
from app.modules.drivers.models import Driver
from tests.integration.test_tenancy_g06b import loading_pair

__all__ = ("loading_pair",)


def test_loading_list_scopes_rows_and_total_before_pagination(client, loading_pair):
    scenario, local, foreign = loading_pair
    response = client.get(
        "/api/v1/loading-sessions",
        headers={
            **scenario.admin_headers,
            "X-Organization-ID": str(foreign["organization"]),
        },
        params={"status": "IN_PROGRESS", "page_size": 1},
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert [item["id"] for item in response.json()["items"]] == [local["id"]]


def test_loading_agenda_keeps_foreign_session_out_of_local_events(
    client, session_factory, loading_pair
):
    scenario, local, foreign = loading_pair
    with session_factory() as db:
        driver = Driver(
            organization_id=foreign["organization"],
            name="Motorista fictício G06-B",
            document="52998224725",
            phone="11900000000",
            license_number="98765432100",
            license_category="D",
        )
        db.add(driver)
        db.flush()
        db.add_all(
            (
                Trip(load_plan_id=scenario.load_plan_id, driver_id=scenario.driver_id),
                Trip(load_plan_id=foreign["plan"], driver_id=driver.id),
            )
        )
        db.commit()

    now = datetime.now(UTC)
    response = client.get(
        "/api/v1/operations/agenda",
        headers=scenario.admin_headers,
        params={
            "start": (now - timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=1)).isoformat(),
            "kind": "LOADING_STARTED",
        },
    )
    assert response.status_code == 200, response.text
    assert [event["resource_id"] for event in response.json()["items"]] == [local["id"]]
