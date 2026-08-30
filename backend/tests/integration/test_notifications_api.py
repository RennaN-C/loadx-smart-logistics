from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.integrations.whatsapp import (
    MockWhatsAppProvider,
    OutgoingWhatsAppMessage,
    get_whatsapp_provider,
    mock_whatsapp_provider,
)
from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario
from tests.integration.test_messages_api import finish_loading


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
