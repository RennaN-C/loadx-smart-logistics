import uuid
from dataclasses import dataclass

from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.modules.occurrences.repository import OccurrenceRepository


@dataclass(frozen=True)
class OccurrenceNotificationOrigin:
    trip_id: uuid.UUID
    type: str


class OccurrenceReferenceService:
    """Read-only origin validation; does not expose occurrence content."""

    def __init__(self, db: Session) -> None:
        self.repository = OccurrenceRepository(db)

    def count_occurrences(self) -> int:
        return self.repository.count_all()

    def get_notification_origin(
        self, identifier: uuid.UUID
    ) -> OccurrenceNotificationOrigin | None:
        occurrence = self.repository.get(identifier)
        return (
            OccurrenceNotificationOrigin(occurrence.trip_id, occurrence.type)
            if occurrence
            else None
        )

    def ids_for_delivery(
        self, delivery_id: uuid.UUID, trip_id: uuid.UUID
    ) -> Select[tuple[uuid.UUID]]:
        """Exact persisted delivery origins, without occurrence content or inference."""
        return self.repository.ids_for_delivery(delivery_id, trip_id)
