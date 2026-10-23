import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.notifications.models import OperationalNotification
from app.modules.notifications.outbox_models import OutboxEvent


class DeliveryCommunicationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def page(
        self,
        trip_id: uuid.UUID,
        occurrence_ids: Select[tuple[uuid.UUID]],
        pagination: PaginationParams,
    ) -> PageResult:
        notification = OperationalNotification
        query = (
            select(
                notification.id,
                notification.occurrence_id,
                notification.event_type,
                notification.created_at,
                notification.mock_status.label("simulation_status"),
                OutboxEvent.status.label("processing_status"),
            )
            .outerjoin(OutboxEvent, OutboxEvent.notification_id == notification.id)
            .where(
                notification.trip_id == trip_id,
                notification.event_type == "OCCURRENCE_REGISTERED",
                notification.occurrence_id.in_(occurrence_ids),
            )
        )
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        ordering = (notification.created_at, notification.id)
        if pagination.sort_order == "desc":
            ordering = tuple(column.desc() for column in ordering)
        rows = (
            self.db.execute(
                query.order_by(*ordering)
                .offset(pagination.offset)
                .limit(pagination.page_size)
            )
            .mappings()
            .all()
        )
        return PageResult.create(rows, pagination, total)
