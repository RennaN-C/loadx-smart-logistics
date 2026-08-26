import uuid

from sqlalchemy.orm import Session

from app.modules.loading.repository import LoadingRepository


class LoadingReferenceService:
    """Public loading boundary consumed by operational modules.

    Loading persistence belongs to its own occurrence. Until that module records
    a finished session, the safe answer is always false.
    """

    def __init__(self, db: Session) -> None:
        self.repository = LoadingRepository(db)

    def is_load_plan_finished(self, load_plan_id: uuid.UUID) -> bool:
        session = self.repository.get_by_load_plan_id(load_plan_id)
        return session is not None and session.status == "FINISHED"
