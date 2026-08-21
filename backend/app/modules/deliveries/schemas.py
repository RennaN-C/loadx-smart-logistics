import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.deliveries.models import DELIVERY_STATUS_VALUES, TRIP_STATUS_VALUES


def normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_status(value: str, allowed: tuple[str, ...], field_name: str) -> str:
    normalized = value.strip().upper()
    if normalized not in allowed:
        allowed_values = ", ".join(allowed)
        raise ValueError(f"{field_name} must be one of: {allowed_values}")
    return normalized


class TripCreate(BaseModel):
    load_plan_id: uuid.UUID
    driver_id: uuid.UUID

    model_config = ConfigDict(extra="forbid")


class TripStatusChange(BaseModel):
    status: str = Field(min_length=1, max_length=32)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return normalize_status(value, TRIP_STATUS_VALUES, "status")


class DeliveryStatusChange(BaseModel):
    status: str = Field(min_length=1, max_length=32)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return normalize_status(value, DELIVERY_STATUS_VALUES, "status")


class DeliveryRead(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    order_id: uuid.UUID
    status: str
    sequence: int = Field(gt=0)
    delivered_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("delivered_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value)


class TripRead(BaseModel):
    id: uuid.UUID
    load_plan_id: uuid.UUID
    driver_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    deliveries: list[DeliveryRead]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("started_at", "finished_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        return normalize_utc(value)
