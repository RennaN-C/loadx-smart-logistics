import uuid
from collections.abc import Callable, Sequence
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.status_history.models import AuditEvent, StatusHistory
from app.modules.status_history.repository import (
    AuditEntryRecord,
    StatusHistoryRepository,
)
from app.modules.status_history.schemas import AuditEventCreate, StatusHistoryCreate
from app.modules.users.repository import UserRepository


class StatusHistoryNotFoundError(Exception):
    pass


class StatusHistoryChangedByNotFoundError(Exception):
    pass


class AuditActorNotFoundError(Exception):
    pass


class AuditInvalidPeriodError(Exception):
    pass


class StatusHistoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = StatusHistoryRepository(db)
        self.user_repository = UserRepository(db)

    def list_status_history(
        self,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Sequence[StatusHistory]:
        normalized_entity_type = (
            entity_type.upper() if entity_type is not None else None
        )
        return self.repository.list(normalized_entity_type, entity_id)

    def get_status_history(self, status_history_id: uuid.UUID) -> StatusHistory:
        status_history = self.repository.get(status_history_id)
        if status_history is None:
            raise StatusHistoryNotFoundError
        return status_history

    def record_status_change(self, data: StatusHistoryCreate) -> StatusHistory:
        return self._persist(lambda: self.stage_status_change(data))

    def stage_status_change(self, data: StatusHistoryCreate) -> StatusHistory:
        """Stage one history row for an outer atomic domain transaction."""

        if data.changed_by is not None:
            self._ensure_changed_by_exists(data.changed_by)

        status_history = StatusHistory(**data.model_dump())
        return self.repository.add(status_history)

    def _ensure_changed_by_exists(self, changed_by: uuid.UUID) -> None:
        if self.user_repository.get(changed_by) is None:
            raise StatusHistoryChangedByNotFoundError

    def _persist(self, operation: Callable[[], StatusHistory]) -> StatusHistory:
        try:
            status_history = operation()
            self.db.commit()
            self.db.refresh(status_history)
        except IntegrityError as exc:
            self.db.rollback()
            if get_integrity_constraint_name(exc) == "fk_status_history__users":
                raise StatusHistoryChangedByNotFoundError from exc
            raise
        return status_history


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = StatusHistoryRepository(db)
        self.user_repository = UserRepository(db)

    def list_entries(
        self,
        pagination: PaginationParams,
        *,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        event_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> PageResult[AuditEntryRecord]:
        start_at = self._normalize_datetime(start_at)
        end_at = self._normalize_datetime(end_at)
        if start_at is not None and end_at is not None and start_at > end_at:
            raise AuditInvalidPeriodError

        return self.repository.list_audit_entries(
            pagination,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            event_type=event_type,
            start_at=start_at,
            end_at=end_at,
        )

    def stage_administrative_event(self, data: AuditEventCreate) -> AuditEvent:
        if self.user_repository.get(data.actor_id) is None:
            raise AuditActorNotFoundError

        event = AuditEvent(
            event_type=data.event_type,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            actor_id=data.actor_id,
            changed_fields=",".join(data.changed_fields),
        )
        return self.repository.add_audit_event(event)

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise AuditInvalidPeriodError
        return value.astimezone(timezone.utc)
