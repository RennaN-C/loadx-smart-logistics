import uuid
from collections.abc import Sequence

from sqlalchemy import asc, desc, func, literal, select, true, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.pagination import PaginationParams
from app.modules.notifications.models import (
    NotificationPreference as Preference,
)
from app.modules.notifications.models import (
    NotificationRecipient as Recipient,
)
from app.modules.notifications.models import (
    OperationalNotification as Notification,
)


class InboxRepository:
    def __init__(self, db: Session):
        self.db = db

    def stage_recipients(
        self, notification_id: uuid.UUID, category: str, eligible
    ) -> None:
        accounts = eligible.subquery()
        disabled = (
            select(Preference.user_id)
            .where(
                Preference.user_id == accounts.c.id,
                Preference.category == category,
                Preference.enabled.is_(False),
            )
            .exists()
        )
        self.db.execute(
            insert(Recipient)
            .from_select(
                ["notification_id", "user_id"],
                select(literal(notification_id), accounts.c.id).where(~disabled),
            )
            .on_conflict_do_nothing()
        )

    def visible(
        self,
        user_id: uuid.UUID,
        events: Sequence[str],
        *,
        driver_id=None,
        trip_ids=None,
    ):
        query = (
            select(
                Notification.id,
                Notification.event_type,
                Notification.trip_id,
                Notification.occurrence_id,
                Notification.created_at,
                Recipient.created_at.label("received_at"),
                Recipient.read_at,
            )
            .join(Recipient, Recipient.notification_id == Notification.id)
            .where(Recipient.user_id == user_id, Notification.event_type.in_(events))
        )
        if driver_id is not None:
            query = query.where(
                Notification.recipient_driver_id == driver_id,
                Notification.trip_id.in_(trip_ids),
            )
        return query

    def page(
        self, visible, pagination: PaginationParams, *, event_type=None, read=None
    ):
        scope = visible.cte("inbox")
        statistics = select(
            func.count().filter(scope.c.read_at.is_(None)).label("unread_count")
        ).cte("stats")
        filtered = select(scope)
        if event_type is not None:
            filtered = filtered.where(scope.c.event_type == event_type)
        if read is not None:
            filtered = filtered.where(
                scope.c.read_at.is_not(None) if read else scope.c.read_at.is_(None)
            )
        filtered = filtered.cte("filtered")
        totals = select(func.count().label("total")).select_from(filtered).cte("totals")
        direction = asc if pagination.sort_order == "asc" else desc
        page = (
            select(filtered)
            .order_by(direction(filtered.c.created_at), direction(filtered.c.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .subquery()
        )
        rows = (
            self.db.execute(
                select(page, statistics.c.unread_count, totals.c.total)
                .select_from(statistics.join(totals, true()).outerjoin(page, true()))
                .order_by(direction(page.c.created_at), direction(page.c.id))
            )
            .mappings()
            .all()
        )
        return (
            [row for row in rows if row["id"] is not None],
            rows[0]["total"],
            rows[0]["unread_count"],
        )

    def unread_count(self, visible) -> int:
        scope = visible.subquery()
        return (
            self.db.scalar(
                select(func.count()).select_from(scope).where(scope.c.read_at.is_(None))
            )
            or 0
        )

    def get(self, visible, identifier):
        scope = visible.subquery()
        return (
            self.db.execute(select(scope).where(scope.c.id == identifier))
            .mappings()
            .first()
        )

    def mark_read(self, visible, user_id, identifier=None) -> int:
        scope = visible.subquery()
        statement = update(Recipient).where(
            Recipient.user_id == user_id,
            Recipient.notification_id.in_(select(scope.c.id)),
            Recipient.read_at.is_(None),
        )
        if identifier is not None:
            statement = statement.where(Recipient.notification_id == identifier)
        return self.db.execute(statement.values(read_at=func.now())).rowcount

    def preferences(self, user_id):
        return dict(
            self.db.execute(
                select(Preference.category, Preference.enabled).where(
                    Preference.user_id == user_id
                )
            ).all()
        )

    def save_preferences(self, user_id, items) -> list[str]:
        changed = []
        for item in items:
            statement = insert(Preference).values(
                user_id=user_id, category=item.category, enabled=item.enabled
            )
            result = self.db.scalar(
                statement.on_conflict_do_update(
                    index_elements=[Preference.user_id, Preference.category],
                    set_={
                        "enabled": statement.excluded.enabled,
                        "updated_at": func.now(),
                    },
                    where=Preference.enabled != statement.excluded.enabled,
                ).returning(Preference.category)
            )
            if result is not None:
                changed.append(result)
        return changed
