"""OC94 exception attempt contracts."""
import uuid
from datetime import UTC, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ExceptionCode = Literal["CUSTOMER_ABSENT", "REFUSED", "DAMAGED", "OPERATIONAL_FAILURE", "RESCHEDULED", "RESUMED"]


class DeliveryExceptionCreate(BaseModel):
    code: ExceptionCode
    reason: str = Field(min_length=10, max_length=1000)
    idempotency_key: uuid.UUID
    scheduled_for: datetime | None = None
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("scheduled_for")
    @classmethod
    def ensure_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.tzinfo.utcoffset(value) is None):
            raise ValueError("scheduled_for must include timezone")
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def validate_schedule(self):
        if (self.code == "RESCHEDULED") != (self.scheduled_for is not None):
            raise ValueError("scheduled_for is required only for RESCHEDULED")
        return self


class DeliveryExceptionRead(BaseModel):
    id: uuid.UUID
    delivery_id: uuid.UUID
    trip_id: uuid.UUID
    code: ExceptionCode
    reason: str
    actor_id: uuid.UUID
    idempotency_key: uuid.UUID
    scheduled_for: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
