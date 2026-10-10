import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import String, asc, desc, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.status_history.models import AuditEvent, StatusHistory
from app.modules.users.models import User


@dataclass(frozen=True, slots=True)
class AuditEntryRecord:
    id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_name: str | None
    old_status: str | None
    new_status: str | None
    changed_fields: tuple[str, ...]
    created_at: datetime


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

    def add_audit_event(self, audit_event: AuditEvent) -> AuditEvent:
        self.db.add(audit_event)
        self.db.flush()
        self.db.refresh(audit_event)
        return audit_event

    def list_audit_entries(
        self,
        pagination: PaginationParams,
        *,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        event_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        exclude_company: bool = False,
    ) -> PageResult[AuditEntryRecord]:
        statements = []

        if event_type in {None, "STATUS_CHANGED"}:
            status_statement = (
                select(
                    StatusHistory.id.label("id"),
                    literal("STATUS_CHANGED").label("event_type"),
                    StatusHistory.entity_type.label("entity_type"),
                    StatusHistory.entity_id.label("entity_id"),
                    StatusHistory.changed_by.label("actor_id"),
                    User.name.label("actor_name"),
                    StatusHistory.old_status.label("old_status"),
                    StatusHistory.new_status.label("new_status"),
                    literal(None, type_=String(512)).label("changed_fields"),
                    StatusHistory.created_at.label("created_at"),
                )
                .select_from(StatusHistory)
                .outerjoin(User, User.id == StatusHistory.changed_by)
            )
            if entity_type is not None:
                status_statement = status_statement.where(
                    StatusHistory.entity_type == entity_type
                )
            if entity_id is not None:
                status_statement = status_statement.where(
                    StatusHistory.entity_id == entity_id
                )
            if actor_id is not None:
                status_statement = status_statement.where(
                    StatusHistory.changed_by == actor_id
                )
            if start_at is not None:
                status_statement = status_statement.where(
                    StatusHistory.created_at >= start_at
                )
            if end_at is not None:
                status_statement = status_statement.where(
                    StatusHistory.created_at <= end_at
                )
            statements.append(status_statement)

        if event_type in {
            None,
            "USER_CREATED",
            "USER_UPDATED",
            "COMPANY_PROFILE_CREATED",
            "COMPANY_PROFILE_UPDATED",
        }:
            audit_statement = (
                select(
                    AuditEvent.id.label("id"),
                    AuditEvent.event_type.label("event_type"),
                    AuditEvent.entity_type.label("entity_type"),
                    AuditEvent.entity_id.label("entity_id"),
                    AuditEvent.actor_id.label("actor_id"),
                    User.name.label("actor_name"),
                    literal(None, type_=String(32)).label("old_status"),
                    literal(None, type_=String(32)).label("new_status"),
                    AuditEvent.changed_fields.label("changed_fields"),
                    AuditEvent.created_at.label("created_at"),
                )
                .select_from(AuditEvent)
                .join(User, User.id == AuditEvent.actor_id)
            )
            if exclude_company:
                audit_statement = audit_statement.where(
                    AuditEvent.entity_type != "COMPANY_PROFILE"
                )
            if event_type is not None:
                audit_statement = audit_statement.where(
                    AuditEvent.event_type == event_type
                )
            if entity_type is not None:
                audit_statement = audit_statement.where(
                    AuditEvent.entity_type == entity_type
                )
            if entity_id is not None:
                audit_statement = audit_statement.where(
                    AuditEvent.entity_id == entity_id
                )
            if actor_id is not None:
                audit_statement = audit_statement.where(AuditEvent.actor_id == actor_id)
            if start_at is not None:
                audit_statement = audit_statement.where(
                    AuditEvent.created_at >= start_at
                )
            if end_at is not None:
                audit_statement = audit_statement.where(AuditEvent.created_at <= end_at)
            statements.append(audit_statement)

        if not statements:
            return PageResult.create([], pagination, 0)

        combined = (
            statements[0].subquery("audit_entries")
            if len(statements) == 1
            else union_all(*statements).subquery("audit_entries")
        )
        total = self.db.scalar(select(func.count()).select_from(combined)) or 0
        direction = asc if pagination.sort_order == "asc" else desc
        rows = self.db.execute(
            select(combined)
            .order_by(direction(combined.c.created_at), direction(combined.c.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).mappings()

        items = [
            AuditEntryRecord(
                id=row["id"],
                event_type=row["event_type"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                actor_id=row["actor_id"],
                actor_name=row["actor_name"],
                old_status=row["old_status"],
                new_status=row["new_status"],
                changed_fields=tuple(
                    field for field in (row["changed_fields"] or "").split(",") if field
                ),
                created_at=row["created_at"],
            )
            for row in rows
        ]
        return PageResult.create(items, pagination, total)
