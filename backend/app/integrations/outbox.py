"""Approved output transport only. No inbound webhook reused as an output channel."""

from dataclasses import dataclass, field
from typing import Protocol

from app.integrations.whatsapp import MockWhatsAppProvider, OutgoingWhatsAppMessage


@dataclass(frozen=True)
class DeliveryEnvelope:
    recipient_phone: str = field(repr=False)
    content: str = field(repr=False)
    idempotency_key: str


class TransientDeliveryError(Exception):
    """A transport guarantees that no effect occurred; a retry is safe."""


class PermanentDeliveryError(Exception):
    """Definitive rejection; manual intervention is required."""


class OutboxTransport(Protocol):
    def send(self, envelope: DeliveryEnvelope) -> None: ...


class MockOutboxTransport:
    def __init__(self, provider: MockWhatsAppProvider | None = None) -> None:
        self.provider = provider or MockWhatsAppProvider()

    def send(self, envelope: DeliveryEnvelope) -> None:
        # This adapter is explicitly mock, never selects a real Meta provider.
        self.provider.send_response(
            OutgoingWhatsAppMessage(
                recipient_phone=envelope.recipient_phone,
                content=envelope.content,
            )
        )
        # The worker keeps no in-memory history containing phone/content.
        self.provider.sent_messages.clear()
