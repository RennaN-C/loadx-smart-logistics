import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.loading.models import LoadingSession
from app.modules.loading.repository import LoadingRepository
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID


class LoadingReferenceService:
    """Public, fail-closed loading boundary consumed by operational modules."""

    def __init__(
        self, db: Session, organization_id: uuid.UUID = LEGACY_ORGANIZATION_ID
    ) -> None:
        self.repository = LoadingRepository(db, organization_id)

    @staticmethod
    def plan_operation_projection(organization_id: uuid.UUID = LEGACY_ORGANIZATION_ID):
        return (
            select(
                LoadingSession.load_plan_id,
                LoadingSession.id.label("loading_session_id"),
                LoadingSession.status.label("loading_status"),
            )
            .where(LoadingSession.organization_id == organization_id)
            .subquery()
        )

    def is_load_plan_finished(self, load_plan_id: uuid.UUID) -> bool:
        session = self.repository.get_by_load_plan_id(load_plan_id)
        return session is not None and session.status == "FINISHED"

    def list_sessions(
        self, pagination: PaginationParams, *, status: str | None = None
    ) -> PageResult[LoadingSession]:
        return self.repository.list(pagination, status=status)

    def get_by_load_plan_id(self, load_plan_id: uuid.UUID) -> LoadingSession | None:
        return self.repository.get_by_load_plan_id(load_plan_id)
