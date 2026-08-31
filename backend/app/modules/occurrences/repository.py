import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.occurrences.models import Occurrence


class OccurrenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, occurrence: Occurrence) -> Occurrence:
        self.db.add(occurrence)
        self.db.flush()
        self.db.refresh(occurrence)
        return occurrence

    def list_by_trip_id(self, trip_id: uuid.UUID) -> list[Occurrence]:
        statement = (
            select(Occurrence)
            .where(Occurrence.trip_id == trip_id)
            .order_by(Occurrence.created_at, Occurrence.id)
        )
        return list(self.db.scalars(statement))
