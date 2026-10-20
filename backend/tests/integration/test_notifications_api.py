import json
import logging
import uuid
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.integrations.whatsapp import (
    MockWhatsAppProvider,
    OutgoingWhatsAppMessage,
    get_whatsapp_provider,
    mock_whatsapp_provider,
)
from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario
from tests.integration.test_messages_api import finish_loading


@pytest.fixture
def session_factory(postgres_engine):
    """HTTP notification tests need durable commits visible to independent Sessions."""
    factory = sessionmaker(bind=postgres_engine, autoflush=False)
    try:
        yield factory
    finally:
        # postgres_engine validates the exclusive loadx_test database before use.
        with postgres_engine.begin() as connection:
            connection.execute(
                text("TRUNCATE customers, products, trucks, drivers, users CASCADE")
            )


@pytest.fixture
def notification_provider() -> Iterator[MockWhatsAppProvider]:
    mock_whatsapp_provider.received_messages.clear()
    mock_whatsapp_provider.sent_messages.clear()
    yield mock_whatsapp_provider
    mock_whatsapp_provider.received_messages.clear()
    mock_whatsapp_provider.sent_messages.clear()


def test_trip_start_notifies_once_after_confirmed_transition(
    client: TestClient,
    session_factory,
    notification_provider: MockWhatsAppProvider,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    finish_loading(client, scenario)

    started = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=scenario.manager_headers,
    )
    repeated = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=scenario.manager_headers,
    )

    assert started.status_code == 200
    assert repeated.status_code == 200
    assert len(notification_provider.sent_messages) == 1
    assert notification_provider.sent_messages[0].recipient_phone == "5500000000000"
    assert notification_provider.sent_messages[0].content == (
        f"Viagem {trip['id']} iniciada."
    )


def test_rejected_trip_start_does_not_notify(
    client: TestClient,
    session_factory,
    notification_provider: MockWhatsAppProvider,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)

    rejected = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=scenario.manager_headers,
    )

    assert rejected.status_code == 409
    assert rejected.json()["code"] == "TRIP_LOADING_NOT_FINISHED"
    assert notification_provider.sent_messages == []


def test_registered_occurrence_notifies_assigned_driver(
    client: TestClient,
    session_factory,
    notification_provider: MockWhatsAppProvider,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)

    created = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": trip["id"],
            "delivery_id": trip["deliveries"][0]["id"],
            "type": "DAMAGED_PRODUCT",
            "description": "Avaria controlada para teste.",
        },
        headers=scenario.manager_headers,
    )

    assert created.status_code == 201
    assert len(notification_provider.sent_messages) == 1
    assert notification_provider.sent_messages[0].recipient_phone == "5500000000000"
    assert notification_provider.sent_messages[0].content == (
        f"Ocorrência DAMAGED_PRODUCT registrada na viagem {trip['id']}."
    )


def test_rejected_occurrence_does_not_notify(
    client: TestClient,
    session_factory,
    notification_provider: MockWhatsAppProvider,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)

    rejected = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": trip["id"],
            "delivery_id": str(uuid.uuid4()),
            "type": "DAMAGED_PRODUCT",
            "description": "Entrega inválida para teste.",
            "photo_url": "mock://occurrences/rejected-photo",
        },
        headers=scenario.manager_headers,
    )

    assert rejected.status_code == 404
    assert rejected.json()["code"] == "DELIVERY_NOT_FOUND"
    assert notification_provider.sent_messages == []


def test_provider_failure_does_not_rollback_confirmed_trip_start(
    client: TestClient,
    session_factory,
) -> None:
    class FailingWhatsAppProvider(MockWhatsAppProvider):
        def send_response(
            self,
            message: OutgoingWhatsAppMessage,
        ) -> OutgoingWhatsAppMessage:
            raise RuntimeError("controlled provider failure")

    app = client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_whatsapp_provider] = FailingWhatsAppProvider
    try:
        scenario = seed_operational_scenario(session_factory)
        trip = create_trip(client, scenario)
        finish_loading(client, scenario)

        started = client.patch(
            f"/api/v1/trips/{trip['id']}/status",
            json={"status": "IN_ROUTE"},
            headers=scenario.manager_headers,
        )
        persisted = client.get(
            f"/api/v1/trips/{trip['id']}",
            headers=scenario.manager_headers,
        )
    finally:
        app.dependency_overrides.pop(get_whatsapp_provider, None)

    assert started.status_code == 200
    assert started.json()["status"] == "IN_ROUTE"
    assert persisted.status_code == 200
    assert persisted.json()["status"] == "IN_ROUTE"


def test_mock_trace_uses_server_request_id_and_gets_have_no_notification_effects(
    client: TestClient,
    session_factory,
    notification_provider: MockWhatsAppProvider,
    caplog: pytest.LogCaptureFixture,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    finish_loading(client, scenario)
    with caplog.at_level(logging.INFO, logger="loadx.operations"):
        started = client.patch(
            f"/api/v1/trips/{trip['id']}/status",
            json={"status": "IN_ROUTE"},
            headers={**scenario.manager_headers, "X-Request-ID": "private-injected-id"},
        )
        for path in (
            "/api/v1/trips",
            f"/api/v1/trips/{trip['id']}",
            f"/api/v1/trips/{trip['id']}/occurrences",
        ):
            assert client.get(path, headers=scenario.manager_headers).status_code == 200

    assert started.status_code == 200
    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "loadx.operations"
        and json.loads(record.getMessage())["event"].startswith("NOTIFICATION_")
    ]
    assert len(notification_provider.sent_messages) == len(events) == 1
    assert events[0]["event"] == "NOTIFICATION_SIMULATED"
    assert events[0]["correlation_id"] == started.headers["x-request-id"]
    assert events[0]["trip_id"] == trip["id"]
    assert "5500000000000" not in caplog.text
    assert "private-injected-id" not in caplog.text
    assert f"Viagem {trip['id']} iniciada." not in caplog.text


@pytest.mark.parametrize("action", ["trip_start", "occurrence"])
@pytest.mark.parametrize(
    ("headers_name", "expected_status"),
    [(None, 401), ("checker_headers", 403), ("other_driver_headers", 403)],
)
def test_unauthorized_operations_do_not_simulate_notifications(
    action: str,
    headers_name: str | None,
    expected_status: int,
    client: TestClient,
    session_factory,
    notification_provider: MockWhatsAppProvider,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    headers = getattr(scenario, headers_name) if headers_name else {}
    if action == "trip_start":
        response = client.patch(
            f"/api/v1/trips/{trip['id']}/status",
            json={"status": "IN_ROUTE"},
            headers=headers,
        )
    else:
        response = client.post(
            "/api/v1/occurrences",
            json={"trip_id": trip["id"], "type": "DELAY", "description": "Teste."},
            headers=headers,
        )
    assert response.status_code == expected_status
    assert notification_provider.sent_messages == []
    assert (
        client.get(
            f"/api/v1/trips/{trip['id']}", headers=scenario.manager_headers
        ).json()["status"]
        == "SCHEDULED"
    )
    assert (
        client.get(
            f"/api/v1/trips/{trip['id']}/occurrences", headers=scenario.manager_headers
        ).json()
        == []
    )
