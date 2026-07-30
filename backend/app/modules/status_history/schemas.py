import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_upper(value: str | None) -> str | None:
    if value is None:
        return None
    return value.upper()


class StatusHistoryBase(BaseModel):
    entity_type: str = Field(min_length=1, max_length=64)
    entity_id: uuid.UUID
    old_status: str | None = Field(default=None, min_length=1, max_length=32)
    new_status: str = Field(min_length=1, max_length=32)
    changed_by: uuid.UUID | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("entity_type", "old_status", "new_status")
    @classmethod
    def normalize_status_text(cls, value: str | None) -> str | None:
        return normalize_upper(value)


class StatusHistoryCreate(StatusHistoryBase):
    pass


class StatusHistoryRead(StatusHistoryBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
