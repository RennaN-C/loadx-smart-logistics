import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.loading.models import LoadingSession
from app.modules.loading.repository import LoadingRepository


class LoadingReferenceService:
    """Public, fail-closed loading boundary consumed by operational modules."""

    def __init__(self, db: Session) -> None:
        self.repository = LoadingRepository(db)

    @staticmethod
    def plan_operation_projection():
        return select(
            LoadingSession.load_plan_id,
            LoadingSession.id.label("loading_session_id"),
            LoadingSession.status.label("loading_status"),
        ).subquery()

    def is_load_plan_finished(self, load_plan_id: uuid.UUID) -> bool:
        session = self.repository.get_by_load_plan_id(load_plan_id)
        return session is not None and session.status == "FINISHED"

    def get_by_load_plan_id(self, load_plan_id: uuid.UUID) -> LoadingSession | None:
        return self.repository.get_by_load_plan_id(load_plan_id)
