"""Fixture cleanup only; application never deletes channel history."""

from sqlalchemy import delete, select

from app.modules.notifications.models import OperationalNotification
from app.modules.notifications.outbox_models import (
    OutboxAttempt,
    OutboxEvent,
    OutboxRetryCommand,
)
from app.modules.status_history.models import AuditEvent


def clear_outbox_fixture(db, trip_id=None):
    events = select(OutboxEvent.id)
    if trip_id is not None:
        events = events.where(
            OutboxEvent.notification_id.in_(
                select(OperationalNotification.id).where(
                    OperationalNotification.trip_id == trip_id
                )
            )
        )
    db.execute(delete(OutboxAttempt).where(OutboxAttempt.outbox_event_id.in_(events)))
    db.execute(
        delete(OutboxRetryCommand).where(OutboxRetryCommand.outbox_event_id.in_(events))
    )
    db.execute(
        delete(AuditEvent).where(
            AuditEvent.entity_type == "OUTBOX_EVENT", AuditEvent.entity_id.in_(events)
        )
    )
    db.execute(delete(OutboxEvent).where(OutboxEvent.id.in_(events)))
