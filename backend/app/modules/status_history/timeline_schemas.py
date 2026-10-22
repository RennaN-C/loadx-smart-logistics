"""Stable, privacy-minimal timeline projection of durable operational facts."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class TimelineEventRead(BaseModel):
    id: uuid.UUID
    source: str
    kind: str
    entity_id: uuid.UUID
    occurred_at: datetime
    actor_id: uuid.UUID | None = None
    status_before: str | None = None
    status_after: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def timezone_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class TimelinePage(BaseModel):
    items: list[TimelineEventRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


def order_unique_events(
    events: list[TimelineEventRead],
) -> list[TimelineEventRead]:
    unique: dict[tuple[str, uuid.UUID], TimelineEventRead] = {}
    for event in events:
        unique[(event.source, event.id)] = event
    return sorted(
        unique.values(),
        key=lambda item: (item.occurred_at, item.source, item.id.int),
    )
