import uuid

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PageResult, PaginationParams
from app.modules.loading.models import LoadingSession, LoadingSessionItem
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID


class LoadingRepository:
    def __init__(
        self, db: Session, organization_id: uuid.UUID = LEGACY_ORGANIZATION_ID
    ) -> None:
        self.db = db
        self.organization_id = organization_id

    def get(self, session_id: uuid.UUID) -> LoadingSession | None:
        statement = (
            select(LoadingSession)
            .where(
                LoadingSession.organization_id == self.organization_id,
                LoadingSession.id == session_id,
            )
            .options(selectinload(LoadingSession.items))
        )
        return self.db.scalar(statement)

    def list(
        self, pagination: PaginationParams, *, status: str | None = None
    ) -> PageResult[LoadingSession]:
        filters = [LoadingSession.organization_id == self.organization_id]
        if status is not None:
            filters.append(LoadingSession.status == status)
        total = (
            self.db.scalar(select(func.count(LoadingSession.id)).where(*filters)) or 0
        )
        direction = asc if pagination.sort_order == "asc" else desc
        rows = self.db.scalars(
            select(LoadingSession)
            .where(*filters)
            .order_by(direction(LoadingSession.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PageResult.create(rows, pagination, total)

    def get_for_update(self, session_id: uuid.UUID) -> LoadingSession | None:
        statement = (
            select(LoadingSession)
            .where(
                LoadingSession.organization_id == self.organization_id,
                LoadingSession.id == session_id,
            )
            .options(selectinload(LoadingSession.items))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(statement)

    def get_by_load_plan_id(self, load_plan_id: uuid.UUID) -> LoadingSession | None:
        statement = (
            select(LoadingSession)
            .where(
                LoadingSession.organization_id == self.organization_id,
                LoadingSession.load_plan_id == load_plan_id,
            )
            .options(selectinload(LoadingSession.items))
        )
        return self.db.scalar(statement)

    def get_item_for_update(self, item_id: uuid.UUID) -> LoadingSessionItem | None:
        statement = (
            select(LoadingSessionItem)
            .where(
                LoadingSessionItem.organization_id == self.organization_id,
                LoadingSessionItem.id == item_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(statement)

    def add(self, session: LoadingSession) -> LoadingSession:
        if session.organization_id != self.organization_id:
            raise ValueError("Loading session belongs to a different organization")
        if any(
            item.organization_id != self.organization_id
            or item.load_plan_id != session.load_plan_id
            for item in session.items
        ):
            raise ValueError("Loading item belongs to a different organization or plan")
        self.db.add(session)
        self.db.flush()
        return session
