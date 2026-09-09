import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.status_history.models import StatusHistory


class StatusHistoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self, entity_type: str | None = None, entity_id: uuid.UUID | None = None
    ) -> Sequence[StatusHistory]:
        statement = select(StatusHistory).order_by(StatusHistory.created_at.desc())
        if entity_type is not None:
            statement = statement.where(StatusHistory.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(StatusHistory.entity_id == entity_id)
        return self.db.scalars(statement).all()

    def get(self, status_history_id: uuid.UUID) -> StatusHistory | None:
        return self.db.get(StatusHistory, status_history_id)

    def add(self, status_history: StatusHistory) -> StatusHistory:
        self.db.add(status_history)
        self.db.flush()
        self.db.refresh(status_history)
        return status_history
