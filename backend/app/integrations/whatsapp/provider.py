"""Port independente do fornecedor, DTOs e provider falso."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.integrations.whatsapp.idempotency import InMemorySendGuard, send_fingerprint


@dataclass(frozen=True, slots=True)
class IncomingWhatsAppMessage:
    """Mensagem recebida pelo adapter, antes de qualquer regra de negócio."""

    sender_phone: str = field(repr=False)
    content: str = field(repr=False)
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class OutgoingWhatsAppMessage:
    """Resposta enviada pelo adapter ao motorista."""

    recipient_phone: str = field(repr=False)
    content: str = field(repr=False)
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    operation_id: uuid.UUID | None = None
    provider_message_id: str | None = field(default=None, repr=False)
    accepted_at: datetime | None = None


class WhatsAppProvider(Protocol):
    """Interface mínima compartilhada por providers mock e reais."""

    def receive_message(
        self, message: IncomingWhatsAppMessage
    ) -> IncomingWhatsAppMessage:
        """Recebe uma mensagem sem interpretá-la ou executá-la."""

    def send_response(
        self, message: OutgoingWhatsAppMessage
    ) -> OutgoingWhatsAppMessage:
        """Envia uma resposta sem acessar serviços de domínio ou banco."""


class MockWhatsAppProvider:
    """Provider em memória para desenvolvimento e testes sem serviço externo."""

    def __init__(self) -> None:
        self._send_guard = InMemorySendGuard()
        self.received_messages: list[IncomingWhatsAppMessage] = []
        self.sent_messages: list[OutgoingWhatsAppMessage] = []

    def receive_message(
        self, message: IncomingWhatsAppMessage
    ) -> IncomingWhatsAppMessage:
        self.received_messages.append(message)
        return message

    def send_response(
        self, message: OutgoingWhatsAppMessage
    ) -> OutgoingWhatsAppMessage:
        if message.operation_id is not None:
            receipt = self._send_guard.claim(
                message.operation_id,
                send_fingerprint(message.recipient_phone, message.content),
            )
            if receipt is not None:
                return receipt
        self.sent_messages.append(message)
        if message.operation_id is not None:
            self._send_guard.complete(message.operation_id, message)
        return message


mock_whatsapp_provider = MockWhatsAppProvider()


def get_mock_whatsapp_provider() -> WhatsAppProvider:
    """Simulação interna nunca usa credenciais ou IO externo."""
    return mock_whatsapp_provider


def get_whatsapp_provider() -> WhatsAppProvider:
    """Composição configurável; falha real não vira sucesso simulado."""
    return mock_whatsapp_provider
