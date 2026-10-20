import logging
import uuid

from app.core.observability import (
    OperationalEvent,
    emit_operational_event,
    request_id_context,
)
from app.integrations.whatsapp import OutgoingWhatsAppMessage, WhatsAppProvider


class OperationalNotificationService:
    """Simula avisos best-effort; o retorno não comprova persistência ou entrega."""

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
            trip_id=trip_id,
            notification_type="TRIP_STARTED",
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
            trip_id=trip_id,
            notification_type="OCCURRENCE_REGISTERED",
        )

    def _send(
        self,
        recipient_phone: str | None,
        content: str,
        *,
        trip_id: uuid.UUID,
        notification_type: str,
    ) -> bool:
        context = {
            "correlation_id": request_id_context.get() or str(uuid.uuid4()),
            "trip_id": str(trip_id),
            "notification_type": notification_type,
        }
        normalized_phone = (recipient_phone or "").strip()
        if not normalized_phone:
            emit_operational_event(
                OperationalEvent.NOTIFICATION_SKIPPED,
                level=logging.WARNING,
                reason="RECIPIENT_MISSING",
                **context,
            )
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
                **context,
            )
            return False
        emit_operational_event(
            OperationalEvent.NOTIFICATION_SIMULATED,
            reason="MOCK_RETURNED",
            **context,
        )
        return True
