import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.loading.models import LoadingSession, LoadingSessionItem


class LoadingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, session_id: uuid.UUID) -> LoadingSession | None:
        statement = (
            select(LoadingSession)
            .where(LoadingSession.id == session_id)
            .options(selectinload(LoadingSession.items))
        )
        return self.db.scalar(statement)

    def get_for_update(self, session_id: uuid.UUID) -> LoadingSession | None:
        statement = (
            select(LoadingSession)
            .where(LoadingSession.id == session_id)
            .options(selectinload(LoadingSession.items))
            .with_for_update()
        )
        return self.db.scalar(statement)

    def get_by_load_plan_id(self, load_plan_id: uuid.UUID) -> LoadingSession | None:
        statement = (
            select(LoadingSession)
            .where(LoadingSession.load_plan_id == load_plan_id)
            .options(selectinload(LoadingSession.items))
        )
        return self.db.scalar(statement)

    def get_item_for_update(self, item_id: uuid.UUID) -> LoadingSessionItem | None:
        statement = (
            select(LoadingSessionItem)
            .where(LoadingSessionItem.id == item_id)
            .with_for_update()
        )
        return self.db.scalar(statement)

    def add(self, session: LoadingSession) -> LoadingSession:
        self.db.add(session)
        self.db.flush()
        return session
