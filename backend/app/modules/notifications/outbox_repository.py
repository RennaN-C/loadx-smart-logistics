import uuid
from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy import func, or_, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.core.pagination import PageResult, PaginationParams
from app.modules.notifications.outbox_models import (
    OutboxAttempt,
    OutboxEvent,
    OutboxRetryCommand,
)


class OutboxRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def stage(self, notification) -> None:
        self.db.execute(
            insert(OutboxEvent)
            .values(
                id=uuid.uuid4(),
                notification_id=notification.id,
                event_type=notification.event_type,
                correlation_id=notification.correlation_id,
                idempotency_key=f"notification:{notification.id}:WHATSAPP_MOCK:v1",
            )
            .on_conflict_do_nothing(index_elements=["notification_id"])
        )

    def now(self):
        return self.db.scalar(select(func.clock_timestamp()))

    def get(self, identifier: uuid.UUID, *, lock: bool = False) -> OutboxEvent | None:
        stmt = select(OutboxEvent).where(OutboxEvent.id == identifier)
        if lock:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt.execution_options(populate_existing=True))

    def next_due(self) -> OutboxEvent | None:
        return self.db.scalar(
            select(OutboxEvent)
            .where(
                or_(
                    (OutboxEvent.status.in_(["PENDING", "RETRYABLE"]))
                    & (OutboxEvent.next_attempt_at <= func.clock_timestamp()),
                    (OutboxEvent.status == "PROCESSING")
                    & (OutboxEvent.lease_expires_at <= func.clock_timestamp()),
                )
            )
            .order_by(OutboxEvent.next_attempt_at, OutboxEvent.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )

    def begin_attempt(self, event: OutboxEvent, lease_seconds: int) -> OutboxAttempt:
        now = self.now()
        event.generation += 1
        event.attempt_count += 1
        event.status = "PROCESSING"
        event.updated_at = now
        event.lease_expires_at = now + timedelta(seconds=lease_seconds)
        attempt = OutboxAttempt(
            outbox_event_id=event.id,
            generation=event.generation,
            result="PROCESSING",
            started_at=now,
        )
        self.db.add(attempt)
        self.db.flush()
        return attempt

    def attempt(self, event: OutboxEvent) -> OutboxAttempt:
        return self.db.scalar(
            select(OutboxAttempt).where(
                OutboxAttempt.outbox_event_id == event.id,
                OutboxAttempt.generation == event.generation,
            )
        )

    def attempts(
        self, identifier: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[OutboxAttempt]:
        where = OutboxAttempt.outbox_event_id == identifier
        total = self.db.scalar(
            select(func.count()).select_from(OutboxAttempt).where(where)
        )
        rows = self.db.scalars(
            select(OutboxAttempt)
            .where(where)
            .order_by(OutboxAttempt.generation.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PageResult.create(rows, pagination, total)

    def legacy_attempt(
        self, event: OutboxEvent, notification, status: str, error: str | None
    ) -> None:
        self.db.add(
            OutboxAttempt(
                outbox_event_id=event.id,
                generation=0,
                origin="LEGACY",
                started_at=notification.claimed_at or self.now(),
                finished_at=notification.completed_at or self.now(),
                result=status,
                error_code=error,
            )
        )

    def list(
        self,
        pagination: PaginationParams,
        *,
        status: str | None,
        event_type: str | None,
    ) -> PageResult[OutboxEvent]:
        stmt = select(OutboxEvent)
        if status:
            stmt = stmt.where(OutboxEvent.status == status)
        if event_type:
            stmt = stmt.where(OutboxEvent.event_type == event_type)
        # One snapshot includes a total even when the requested page is empty.
        visible = stmt.cte("visible_outbox")
        model = aliased(OutboxEvent, visible)
        order = (model.created_at, model.id)
        if pagination.sort_order == "desc":
            order = tuple(col.desc() for col in order)
        paged = (
            select(model)
            .order_by(*order)
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .cte("outbox_page")
        )
        total = (
            select(func.count().label("total")).select_from(visible).cte("outbox_total")
        )
        item = aliased(OutboxEvent, paged)
        final_order = (item.created_at, item.id)
        if pagination.sort_order == "desc":
            final_order = tuple(col.desc() for col in final_order)
        records = self.db.execute(
            select(item, total.c.total)
            .select_from(total.outerjoin(paged, true()))
            .order_by(*final_order)
        ).all()
        return PageResult.create(
            [record[0] for record in records if record[0] is not None],
            pagination,
            records[0][1],
        )

    def summary(self) -> Sequence:
        return self.db.execute(
            select(
                OutboxEvent.status, func.count(), func.min(OutboxEvent.created_at)
            ).group_by(OutboxEvent.status)
        ).all()

    def retry_command(
        self, command_id: uuid.UUID, event_id: uuid.UUID, actor_id: uuid.UUID
    ):
        return self.db.scalar(
            insert(OutboxRetryCommand)
            .values(id=command_id, outbox_event_id=event_id, actor_id=actor_id)
            .on_conflict_do_nothing()
            .returning(OutboxRetryCommand.id)
        )

    def get_command(self, identifier: uuid.UUID) -> OutboxRetryCommand:
        return self.db.get(OutboxRetryCommand, identifier)
