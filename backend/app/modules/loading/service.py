import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.load_planning.reference_service import LoadPlanReferenceService
from app.modules.loading.models import LoadingSession, LoadingSessionItem
from app.modules.loading.repository import LoadingRepository


class LoadingSessionNotFoundError(Exception):
    pass


class LoadingPlanNotApprovedError(Exception):
    pass


class LoadingItemNotFoundError(Exception):
    pass


class LoadingItemSessionMismatchError(Exception):
    pass


class LoadingStatusTransitionError(Exception):
    pass


class LoadingChecklistIncompleteError(Exception):
    pass


class LoadingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = LoadingRepository(db)
        self.load_plan_reference_service = LoadPlanReferenceService(db)

    def create_session(self, load_plan_id: uuid.UUID) -> LoadingSession:
        existing = self.repository.get_by_load_plan_id(load_plan_id)
        if existing is not None:
            return existing
        plan = self.load_plan_reference_service.get_operational_plan(load_plan_id)
        items = self.load_plan_reference_service.get_loading_items(load_plan_id)
        if plan is None or plan.status != "APPROVED" or not items:
            raise LoadingPlanNotApprovedError
        session = LoadingSession(
            load_plan_id=load_plan_id,
            status="PENDING",
            items=[LoadingSessionItem(load_plan_item_id=item.id, status="PENDING") for item in items],
        )
        try:
            self.repository.add(session)
            self.db.commit()
            return self._get_session(session.id)
        except Exception:
            self.db.rollback()
            raise

    def get_session(self, session_id: uuid.UUID) -> LoadingSession:
        return self._get_session(session_id)

    def change_status(self, session_id: uuid.UUID, status: str) -> LoadingSession:
        session = self.repository.get_for_update(session_id)
        if session is None:
            raise LoadingSessionNotFoundError
        if status == session.status:
            return session
        if session.status == "PENDING" and status == "IN_PROGRESS":
            session.status = status
            session.started_at = datetime.now(UTC)
        elif session.status == "IN_PROGRESS" and status == "FINISHED":
            if any(item.status != "CHECKED" for item in session.items):
                raise LoadingChecklistIncompleteError
            session.status = status
            session.finished_at = datetime.now(UTC)
        else:
            raise LoadingStatusTransitionError
        self.db.commit()
        return self._get_session(session.id)

    def change_item_status(self, session_id: uuid.UUID, item_id: uuid.UUID, status: str) -> LoadingSession:
        session = self.repository.get_for_update(session_id)
        if session is None:
            raise LoadingSessionNotFoundError
        if session.status != "IN_PROGRESS":
            raise LoadingStatusTransitionError
        item = self.repository.get_item_for_update(item_id)
        if item is None:
            raise LoadingItemNotFoundError
        if item.loading_session_id != session.id:
            raise LoadingItemSessionMismatchError
        if item.status != status:
            if item.status != "PENDING" or status != "CHECKED":
                raise LoadingStatusTransitionError
            item.status = status
            self.db.commit()
        return self._get_session(session.id)

    def _get_session(self, session_id: uuid.UUID) -> LoadingSession:
        session = self.repository.get(session_id)
        if session is None:
            raise LoadingSessionNotFoundError
        return session
