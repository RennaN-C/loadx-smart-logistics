import logging
import uuid

from app.core.observability import OperationalEvent, emit_operational_event
from app.integrations.whatsapp import OutgoingWhatsAppMessage, WhatsAppProvider


class OperationalNotificationService:
    """Envia avisos sobre fatos confirmados sem alterar o estado do domínio."""

    def __init__(self, provider: WhatsAppProvider) -> None:
        self.provider = provider

    def notify_trip_started(
        self,
        *,
        recipient_phone: str | None,
        trip_id: uuid.UUID,
    ) -> bool:
        return self._send(
            recipient_phone,
            f"Viagem {trip_id} iniciada.",
        )

    def notify_occurrence_registered(
        self,
        *,
        recipient_phone: str | None,
        trip_id: uuid.UUID,
        occurrence_type: str,
    ) -> bool:
        return self._send(
            recipient_phone,
            f"Ocorrência {occurrence_type} registrada na viagem {trip_id}.",
        )

    def _send(self, recipient_phone: str | None, content: str) -> bool:
        normalized_phone = (recipient_phone or "").strip()
        if not normalized_phone:
            return False
        try:
            self.provider.send_response(
                OutgoingWhatsAppMessage(
                    recipient_phone=normalized_phone,
                    content=content,
                )
            )
        except Exception as error:  # noqa: BLE001 - notification failure must not undo operation
            emit_operational_event(
                OperationalEvent.NOTIFICATION_FAILED,
                level=logging.WARNING,
                alert=True,
                reason="DELIVERY_FAILED",
                exception_type=type(error).__name__,
            )
            return False
        return True
