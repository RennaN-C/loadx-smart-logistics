import pytest

from app.integrations.whatsapp.provider import (
    IncomingWhatsAppMessage,
    MockWhatsAppProvider,
    OutgoingWhatsAppMessage,
    get_whatsapp_provider,
    mock_whatsapp_provider,
)


def test_application_resolves_shared_mock_provider() -> None:
    assert get_whatsapp_provider() is mock_whatsapp_provider


@pytest.mark.parametrize(
    "message",
    [
        IncomingWhatsAppMessage(sender_phone="+5500000000000", content="STATUS"),
        OutgoingWhatsAppMessage(
            recipient_phone="+5500000000000", content="Mensagem recebida."
        ),
    ],
)
def test_message_representation_omits_phone_and_content(message) -> None:
    representation = repr(message)

    assert "+5500000000000" not in representation
    assert "STATUS" not in representation
    assert "Mensagem recebida." not in representation


def test_mock_whatsapp_provider_receives_message_without_external_service() -> None:
    provider = MockWhatsAppProvider()
    incoming_message = IncomingWhatsAppMessage(
        sender_phone="+5500000000000",
        content="STATUS",
    )

    received_message = provider.receive_message(incoming_message)

    assert received_message == incoming_message
    assert provider.received_messages == [incoming_message]


def test_mock_whatsapp_provider_sends_response_without_external_service() -> None:
    provider = MockWhatsAppProvider()
    outgoing_message = OutgoingWhatsAppMessage(
        recipient_phone="+5500000000000",
        content="Mensagem recebida.",
    )

    sent_message = provider.send_response(outgoing_message)

    assert sent_message == outgoing_message
    assert provider.sent_messages == [outgoing_message]
