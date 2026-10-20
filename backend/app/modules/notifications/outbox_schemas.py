import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.notifications.schemas import EventType

State = Literal[
    "PENDING", "PROCESSING", "SUCCEEDED", "RETRYABLE", "TERMINAL", "UNCERTAIN"
]


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    notification_id: uuid.UUID
    channel: Literal["WHATSAPP_MOCK"]
    event_type: EventType
    contract_version: Literal[1]
    correlation_id: uuid.UUID
    status: State
    attempt_count: int
    generation: int
    next_attempt_at: datetime
    lease_expires_at: datetime | None
    last_error_code: str | None
    created_at: datetime
    updated_at: datetime


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    generation: int
    origin: Literal["LEGACY", "WORKER"]
    started_at: datetime
    finished_at: datetime | None
    result: State
    error_code: str | None


class QueueSummary(BaseModel):
    counts: dict[State, int]
    oldest_pending_at: datetime | None


class RetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: uuid.UUID


class EventSource(BaseModel):
    href: str
