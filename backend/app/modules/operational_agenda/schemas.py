"""Real activity calendar: no invented scheduled departure or ETA."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

AgendaKind = Literal[
    "TRIP_CREATED",
    "TRIP_STARTED",
    "TRIP_FINISHED",
    "LOADING_STARTED",
    "LOADING_FINISHED",
    "DELIVERY_COMPLETED",
    "DELIVERY_EXCEPTION",
    "TRIP_CANCELED",
    "TRIP_INTERRUPTED",
    "TRIP_RESUMED",
]


class AgendaEvent(BaseModel):
    kind: AgendaKind
    resource_id: uuid.UUID
    trip_id: uuid.UUID
    occurred_at: datetime
    truck_id: uuid.UUID
    driver_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)

    @field_validator("occurred_at")
    @classmethod
    def normalize_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class OperationalAgendaRead(BaseModel):
    start: datetime
    end: datetime
    total: int
    items: list[AgendaEvent]
