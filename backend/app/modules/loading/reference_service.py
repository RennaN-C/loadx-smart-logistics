import uuid

from sqlalchemy.orm import Session

from app.modules.loading.repository import LoadingRepository


class LoadingReferenceService:
    """Public, fail-closed loading boundary consumed by operational modules."""

    def __init__(self, db: Session) -> None:
        self.repository = LoadingRepository(db)

    def is_load_plan_finished(self, load_plan_id: uuid.UUID) -> bool:
        session = self.repository.get_by_load_plan_id(load_plan_id)
        return session is not None and session.status == "FINISHED"
