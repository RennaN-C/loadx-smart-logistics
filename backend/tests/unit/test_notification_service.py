import uuid

import pytest

from app.integrations.whatsapp import MockWhatsAppProvider
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
