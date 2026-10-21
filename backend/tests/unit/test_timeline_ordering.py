import uuid
from datetime import UTC, datetime, timedelta

from app.modules.status_history.timeline_schemas import (
    TimelineEventRead,
    order_unique_events,
)


def test_timeline_order_is_deterministic_and_removes_source_duplicates():
    moment = datetime(2026, 10, 21, tzinfo=UTC)
    first = TimelineEventRead(
        id=uuid.UUID(int=1),
        source="STATUS_HISTORY",
        kind="STATUS_CHANGED",
        entity_id=uuid.UUID(int=2),
        occurred_at=moment,
        status_after="IN_ROUTE",
    )
    second = TimelineEventRead(
        id=uuid.UUID(int=3),
        source="OCCURRENCE",
        kind="DELAY",
        entity_id=uuid.UUID(int=2),
        occurred_at=moment + timedelta(minutes=1),
    )
    assert order_unique_events([second, first, first]) == [first, second]


def test_timeline_normalizes_datetime_to_utc():
    naive = datetime(2026, 10, 21, 12)
    event = TimelineEventRead(
        id=uuid.uuid4(),
        source="OCCURRENCE",
        kind="DELAY",
        entity_id=uuid.uuid4(),
        occurred_at=naive,
    )
    assert event.occurred_at.tzinfo == UTC
