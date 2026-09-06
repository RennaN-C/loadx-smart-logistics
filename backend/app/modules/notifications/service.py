import logging
import uuid

from app.integrations.whatsapp import OutgoingWhatsAppMessage, WhatsAppProvider

logger = logging.getLogger(__name__)


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
        except Exception:
            logger.warning(
                "Operational notification delivery failed",
                exc_info=True,
            )
            return False
        return True
