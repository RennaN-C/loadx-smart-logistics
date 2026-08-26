"""Contratos e provider mock para a integração controlada com WhatsApp."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class IncomingWhatsAppMessage:
    """Mensagem recebida pelo adapter, antes de qualquer regra de negócio."""

    sender_phone: str
    content: str
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class OutgoingWhatsAppMessage:
    """Resposta enviada pelo adapter ao motorista."""

    recipient_phone: str
    content: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class WhatsAppProvider(Protocol):
    """Interface mínima compartilhada por providers mock e reais."""

    def receive_message(self, message: IncomingWhatsAppMessage) -> IncomingWhatsAppMessage:
        """Recebe uma mensagem sem interpretá-la ou executá-la."""

    def send_response(self, message: OutgoingWhatsAppMessage) -> OutgoingWhatsAppMessage:
        """Envia uma resposta sem acessar serviços de domínio ou banco."""


class MockWhatsAppProvider:
    """Provider em memória para desenvolvimento e testes sem serviço externo."""

    def __init__(self) -> None:
        self.received_messages: list[IncomingWhatsAppMessage] = []
        self.sent_messages: list[OutgoingWhatsAppMessage] = []

    def receive_message(self, message: IncomingWhatsAppMessage) -> IncomingWhatsAppMessage:
        self.received_messages.append(message)
        return message

    def send_response(self, message: OutgoingWhatsAppMessage) -> OutgoingWhatsAppMessage:
        self.sent_messages.append(message)
        return message
