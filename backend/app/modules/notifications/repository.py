import uuid

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.notifications.models import OperationalNotification


class OperationalNotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, identifier: uuid.UUID) -> OperationalNotification | None:
        return self.db.get(OperationalNotification, identifier)

    def get_for_update(self, identifier: uuid.UUID) -> OperationalNotification:
        return self.db.scalar(
            select(OperationalNotification)
            .where(OperationalNotification.id == identifier)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def record(
        self,
        *,
        event_type: str,
        trip_id: uuid.UUID,
        recipient_driver_id: uuid.UUID,
        status_history_id: uuid.UUID | None,
        occurrence_id: uuid.UUID | None,
        correlation_id: uuid.UUID,
    ) -> tuple[OperationalNotification, bool]:
        values = {
            "event_type": event_type,
            "trip_id": trip_id,
            "recipient_driver_id": recipient_driver_id,
            "status_history_id": status_history_id,
            "occurrence_id": occurrence_id,
            "correlation_id": correlation_id,
        }
        # DO NOTHING waits on a competing insert without poisoning the domain transaction.
        inserted = self.db.scalar(
            insert(OperationalNotification)
            .values(id=uuid.uuid4(), **values)
            .on_conflict_do_nothing()
            .returning(OperationalNotification.id)
        )
        origin_field = (
            "status_history_id"
            if values["event_type"] == "TRIP_STARTED"
            else "occurrence_id"
        )
        row = self.db.scalar(
            select(OperationalNotification).where(
                OperationalNotification.event_type == values["event_type"],
                getattr(OperationalNotification, origin_field) == values[origin_field],
                OperationalNotification.recipient_driver_id
                == values["recipient_driver_id"],
            )
        )
        if row is None:
            raise RuntimeError("notification record unavailable")
        return row, inserted is not None

    def claim(self, identifier: uuid.UUID) -> bool:
        return (
            self.db.scalar(
                update(OperationalNotification)
                .where(
                    OperationalNotification.id == identifier,
                    OperationalNotification.mock_status == "NOT_ATTEMPTED",
                )
                .values(mock_status="ATTEMPT_CLAIMED", claimed_at=func.now())
                .returning(OperationalNotification.id)
            )
            is not None
        )

    def complete(self, identifier: uuid.UUID, status: str) -> None:
        self.db.execute(
            update(OperationalNotification)
            .where(
                OperationalNotification.id == identifier,
                OperationalNotification.mock_status == "ATTEMPT_CLAIMED",
            )
            .values(mock_status=status, completed_at=func.now())
        )
