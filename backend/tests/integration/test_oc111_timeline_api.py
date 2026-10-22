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
    assert (
        client.get(uri, headers=scenario.other_driver_headers).status_code == 403
    )

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
