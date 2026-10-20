import json
import logging
import uuid

import pytest

from app.core.observability import request_id_context
from app.integrations.whatsapp import MockWhatsAppProvider, OutgoingWhatsAppMessage
from app.modules.notifications.service import OperationalNotificationService


def test_notifies_assigned_driver_when_trip_starts() -> None:
    provider = MockWhatsAppProvider()
    service = OperationalNotificationService(provider)
    trip_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    sent = service.notify_trip_started(
        recipient_phone="+5500000000000",
        trip_id=trip_id,
    )

    assert sent is True
    assert len(provider.sent_messages) == 1
    assert provider.sent_messages[0].recipient_phone == "+5500000000000"
    assert provider.sent_messages[0].content == (
        "Viagem 00000000-0000-0000-0000-000000000001 iniciada."
    )


def test_notifies_assigned_driver_when_occurrence_is_registered() -> None:
    provider = MockWhatsAppProvider()
    service = OperationalNotificationService(provider)
    trip_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    sent = service.notify_occurrence_registered(
        recipient_phone="+5500000000001",
        trip_id=trip_id,
        occurrence_type="DAMAGED_PRODUCT",
    )

    assert sent is True
    assert len(provider.sent_messages) == 1
    assert provider.sent_messages[0].recipient_phone == "+5500000000001"
    assert provider.sent_messages[0].content == (
        "Ocorrência DAMAGED_PRODUCT registrada na viagem "
        "00000000-0000-0000-0000-000000000002."
    )


@pytest.mark.parametrize("recipient_phone", [None, "", "   "])
def test_missing_recipient_does_not_send_or_fail_domain(
    recipient_phone: str | None,
) -> None:
    provider = MockWhatsAppProvider()
    service = OperationalNotificationService(provider)
    confirmed_status = "IN_ROUTE"

    sent = service.notify_trip_started(
        recipient_phone=recipient_phone,
        trip_id=uuid.uuid4(),
    )

    assert sent is False
    assert provider.sent_messages == []
    assert confirmed_status == "IN_ROUTE"


def test_provider_failure_is_best_effort() -> None:
    class FailingWhatsAppProvider(MockWhatsAppProvider):
        def send_response(self, message):
            raise RuntimeError("controlled provider failure")

    service = OperationalNotificationService(FailingWhatsAppProvider())

    sent = service.notify_trip_started(
        recipient_phone="+5500000000000",
        trip_id=uuid.uuid4(),
    )

    assert sent is False


@pytest.mark.parametrize("notification_type", ["TRIP_STARTED", "OCCURRENCE_REGISTERED"])
@pytest.mark.parametrize(
    ("outcome", "event_name", "reason"),
    [
        ("simulated", "NOTIFICATION_SIMULATED", "MOCK_RETURNED"),
        ("missing", "NOTIFICATION_SKIPPED", "RECIPIENT_MISSING"),
        ("failed", "NOTIFICATION_FAILED", "DELIVERY_FAILED"),
    ],
)
def test_mock_outcomes_are_correlated_without_claiming_delivery_or_logging_content(
    notification_type: str,
    outcome: str,
    event_name: str,
    reason: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class ControlledMock(MockWhatsAppProvider):
        def send_response(
            self, message: OutgoingWhatsAppMessage
        ) -> OutgoingWhatsAppMessage:
            if outcome == "failed":
                raise RuntimeError(
                    f"phone={message.recipient_phone}; body={message.content}; "
                    "token=fixture-secret; cookie=fixture-cookie; signature=fixture-hmac"
                )
            return super().send_response(message)

    provider = ControlledMock()
    service = OperationalNotificationService(provider)
    trip_id = uuid.uuid4()
    request_id = str(uuid.uuid4())
    token = request_id_context.set(request_id)
    arguments = {"recipient_phone": None if outcome == "missing" else "private-phone"}
    try:
        with caplog.at_level(logging.INFO, logger="loadx.operations"):
            if notification_type == "TRIP_STARTED":
                simulated = service.notify_trip_started(trip_id=trip_id, **arguments)
            else:
                simulated = service.notify_occurrence_registered(
                    trip_id=trip_id, occurrence_type="DELAY", **arguments
                )
    finally:
        request_id_context.reset(token)

    events = [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "loadx.operations"
    ]
    assert simulated is (outcome == "simulated")
    assert len(provider.sent_messages) == int(simulated)
    assert len(events) == 1
    assert events[0]["event"] == event_name
    assert events[0]["reason"] == reason
    assert events[0]["correlation_id"] == events[0]["request_id"] == request_id
    assert events[0]["trip_id"] == str(trip_id)
    assert events[0]["notification_type"] == notification_type
    for marker in (
        "private-phone",
        "fixture-secret",
        "fixture-cookie",
        "fixture-hmac",
        "Viagem ",
        "Ocorrência ",
        "DELIVERED",
        '"SENT"',
    ):
        assert marker not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_mock_outside_http_gets_server_correlation_without_creating_request_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = OperationalNotificationService(MockWhatsAppProvider())
    assert request_id_context.get() is None
    with caplog.at_level(logging.INFO, logger="loadx.operations"):
        service.notify_trip_started(
            recipient_phone="fixture-phone", trip_id=uuid.uuid4()
        )
    payload = json.loads(caplog.records[-1].getMessage())
    assert uuid.UUID(payload["correlation_id"])
    assert payload["request_id"] is None
    assert request_id_context.get() is None
