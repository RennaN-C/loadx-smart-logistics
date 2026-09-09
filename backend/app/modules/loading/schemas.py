import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

LOADING_SESSION_STATUS_VALUES = ("PENDING", "IN_PROGRESS", "FINISHED")
LOADING_ITEM_STATUS_VALUES = ("PENDING", "CHECKED")


class LoadingSessionCreate(BaseModel):
    load_plan_id: uuid.UUID

    model_config = ConfigDict(extra="forbid")


class LoadingSessionStatusChange(BaseModel):
    status: str = Field(min_length=1, max_length=32)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in LOADING_SESSION_STATUS_VALUES:
            raise ValueError("status must be a supported loading session status")
        return normalized


class LoadingItemStatusChange(BaseModel):
    status: str = Field(min_length=1, max_length=32)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in LOADING_ITEM_STATUS_VALUES:
            raise ValueError("status must be a supported loading item status")
        return normalized


class LoadingSessionItemRead(BaseModel):
    id: uuid.UUID
    load_plan_item_id: uuid.UUID
    status: str

    model_config = ConfigDict(from_attributes=True)


class LoadingSessionRead(BaseModel):
    id: uuid.UUID
    load_plan_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    items: list[LoadingSessionItemRead]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("started_at", "finished_at")
    @classmethod
    def normalize_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
