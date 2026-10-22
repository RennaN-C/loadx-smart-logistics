"""PostgreSQL-backed timeline authorization and stable pagination."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_deliveries_api import (
    create_trip,
    seed_operational_scenario,
)

SessionFactory = Callable[[], Session]


def test_oc111_timeline_is_read_only_and_scoped_to_trip(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    uri = f"/api/v1/trips/{trip['id']}/timeline?page=1&page_size=20"

    assert client.get(uri).status_code == 401
    assert client.get(uri, headers=scenario.checker_headers).status_code == 403
    assert client.get(uri, headers=scenario.other_driver_headers).status_code == 403

    for headers in (scenario.manager_headers, scenario.driver_headers):
        response = client.get(uri, headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert body["total"] >= 0
        for event in body["items"]:
            assert "occurred_at" in event
            assert "source" in event
            assert "kind" in event
            assert "reason" not in event
            assert "description" not in event
            assert "photo_url" not in event

    missing = client.get(
        f"/api/v1/trips/{uuid.uuid4()}/timeline",
        headers=scenario.manager_headers,
    )
    assert missing.status_code == 404
    invalid_page = client.get(
        f"/api/v1/trips/{trip['id']}/timeline?page_size=101",
        headers=scenario.manager_headers,
    )
    assert invalid_page.status_code == 422


def test_oc111_cancellation_pages_are_stable_without_replayed_events(
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
    uri = f"/api/v1/trips/{trip['id']}/timeline"
    complete = client.get(uri, headers=scenario.manager_headers).json()
    assert complete["total"] >= 4
    cancellation = [
        row for row in complete["items"] if row["source"] == "TRIP_CANCELLATION"
    ]
    assert len(cancellation) == 1
    assert cancellation[0]["kind"] == "TRIP_CANCELED"
    paged = []
    for page in range(1, complete["total"] + 1):
        params = {"page": page, "page_size": 1}
        first = client.get(uri, params=params, headers=scenario.driver_headers)
        repeated = client.get(uri, params=params, headers=scenario.driver_headers)
        assert first.status_code == repeated.status_code == 200
        assert first.json() == repeated.json()
        paged.extend(first.json()["items"])
    assert paged == complete["items"]
    assert len({(row["source"], row["id"]) for row in paged}) == len(paged)
    empty = client.get(
        uri,
        params={"page": complete["total"] + 1, "page_size": 1},
        headers=scenario.driver_headers,
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["total"] == complete["total"]
