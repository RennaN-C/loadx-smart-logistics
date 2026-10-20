import logging
import uuid
from collections.abc import Callable

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.observability import (
    OperationalEvent,
    emit_operational_event,
    request_id_context,
)
from app.integrations.whatsapp import WhatsAppProvider
from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.drivers.service import DriverService
from app.modules.notifications.repository import OperationalNotificationRepository
from app.modules.notifications.sender import MockNotificationSender
from app.modules.occurrences.reference_service import OccurrenceReferenceService
from app.modules.status_history.service import StatusHistoryService


class OperationalNotificationService:
    """Record domain facts atomically; claim a local mock attempt after durable commit."""

    def __init__(self, provider: WhatsAppProvider | None = None) -> None:
        self.provider = provider

    def stage(
        self,
        db: Session,
        *,
        event_type: str,
        trip_id: uuid.UUID,
        recipient_driver_id: uuid.UUID,
        status_history_id: uuid.UUID | None = None,
        occurrence_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        trip = DeliveryReferenceService(db).get_trip_for_notification(trip_id)
        if trip is None or trip.driver_id != recipient_driver_id:
            raise ValueError("invalid notification recipient")
        self._validate_origin(db, event_type, trip_id, status_history_id, occurrence_id)
        row = OperationalNotificationRepository(db).record(
            event_type=event_type,
            trip_id=trip_id,
            recipient_driver_id=recipient_driver_id,
            status_history_id=status_history_id,
            occurrence_id=occurrence_id,
            correlation_id=uuid.UUID(request_id_context.get())
            if request_id_context.get()
            else uuid.uuid4(),
        )
        # A dispatch hint only; the database row is the durable source of truth.
        db.info.setdefault("operational_notifications", {})[row.id] = self
        return row.id

    @staticmethod
    def _validate_origin(
        db: Session,
        event_type: str,
        trip_id: uuid.UUID,
        status_history_id: uuid.UUID | None,
        occurrence_id: uuid.UUID | None,
    ) -> None:
        if event_type == "TRIP_STARTED":
            if status_history_id is None or occurrence_id is not None:
                raise ValueError("invalid trip notification origin")
            history = StatusHistoryService(db).get_status_history(status_history_id)
            if (
                history.entity_type,
                history.entity_id,
                history.old_status,
                history.new_status,
            ) != (
                "TRIP",
                trip_id,
                "SCHEDULED",
                "IN_ROUTE",
            ):
                raise ValueError("invalid trip notification origin")
        elif event_type == "OCCURRENCE_REGISTERED":
            if occurrence_id is None or status_history_id is not None:
                raise ValueError("invalid occurrence notification origin")
            origin = OccurrenceReferenceService(db).get_notification_origin(
                occurrence_id
            )
            if origin is None or origin.trip_id != trip_id:
                raise ValueError("invalid occurrence notification origin")
        else:
            raise ValueError("unsupported notification event")

    @staticmethod
    def transfer_staged(source: Session, owner: Session) -> None:
        owner.info.setdefault("operational_notifications", {}).update(
            source.info.pop("operational_notifications", {})
        )

    @staticmethod
    def dispatch_after_commit(db: Session) -> None:
        bind = db.get_bind()
        # A Connection-bound Session may only have released a savepoint. Its
        # owner must transfer the hints and call us after its durable commit.
        if not isinstance(bind, Engine) or db.in_transaction():
            return
        pending = db.info.pop("operational_notifications", {})
        factory = sessionmaker(bind=bind, autoflush=False)
        for identifier, service in pending.items():
            service.dispatch(identifier, factory)

    def dispatch(self, identifier: uuid.UUID, factory: Callable[[], Session]) -> None:
        if self.provider is None:
            return
        try:
            with factory() as db, db.begin():
                if not isinstance(db.get_bind(), Engine):
                    return
                claimed = OperationalNotificationRepository(db).claim(identifier)
            if not claimed:
                return
            # Claim is durable before the independent simulation transaction.
            with factory() as db, db.begin():
                self._simulate_claimed(db, identifier)
        except Exception as error:  # noqa: BLE001 - a durable domain event must survive channel failure
            emit_operational_event(
                OperationalEvent.NOTIFICATION_FAILED,
                level=logging.WARNING,
                alert=True,
                reason="ATTEMPT_PROCESSING_FAILED",
                notification_id=str(identifier),
                exception_type=type(error).__name__,
            )

    def _simulate_claimed(self, db: Session, identifier: uuid.UUID) -> None:
        repository = OperationalNotificationRepository(db)
        row = repository.get(identifier)
        trip = DeliveryReferenceService(db).get_trip_for_notification(row.trip_id)
        driver = DriverService(db).get_driver_for_update(row.recipient_driver_id)
        if (
            trip is None
            or trip.driver_id != driver.id
            or not driver.active
            or not (driver.phone or "").strip()
        ):
            result = "NO_RECIPIENT"
            MockNotificationSender(self.provider).send(
                None,
                "",
                trip_id=row.trip_id,
                notification_type=row.event_type,
                correlation_id=row.correlation_id,
                notification_id=row.id,
            )
        else:
            origin = (
                OccurrenceReferenceService(db).get_notification_origin(
                    row.occurrence_id
                )
                if row.occurrence_id
                else None
            )
            content = (
                f"Viagem {row.trip_id} iniciada."
                if row.event_type == "TRIP_STARTED"
                else f"Ocorrência {origin.type} registrada na viagem {row.trip_id}."
            )
            result = (
                "SIMULATED"
                if MockNotificationSender(self.provider).send(
                    driver.phone,
                    content,
                    trip_id=row.trip_id,
                    notification_type=row.event_type,
                    correlation_id=row.correlation_id,
                    notification_id=row.id,
                )
                else "FAILED"
            )
        repository.complete(identifier, result)
