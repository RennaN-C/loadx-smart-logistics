import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

STATUS_HISTORY_ENTITY_TYPES = frozenset(
    {
        "ORDER",
        "LOAD_PLAN",
        "TRIP",
        "DELIVERY",
        "LOAD_DISTRIBUTION",
        "LOAD_DISTRIBUTION_PART",
    }
)
RECORD_ENTITY_TYPES = frozenset(
    {"CUSTOMER", "PRODUCT", "TRUCK", "DRIVER", "CUSTOMER_ADDRESS"}
)
ADMINISTRATIVE_EVENT_TYPES = frozenset(
    {
        "USER_CREATED",
        "USER_UPDATED",
        "RECORD_ARCHIVED",
        "RECORD_REACTIVATED",
        "CUSTOMER_ADDRESS_CREATED",
        "CUSTOMER_ADDRESS_UPDATED",
        "CUSTOMER_ADDRESS_ARCHIVED",
        "CUSTOMER_ADDRESS_REACTIVATED",
    }
)
AUDIT_ENTITY_TYPES = frozenset(
    {*STATUS_HISTORY_ENTITY_TYPES, "USER", *RECORD_ENTITY_TYPES}
)
AUDIT_EVENT_TYPES = frozenset({"STATUS_CHANGED", *ADMINISTRATIVE_EVENT_TYPES})


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

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value: str) -> str:
        if value not in STATUS_HISTORY_ENTITY_TYPES:
            allowed_values = ", ".join(sorted(STATUS_HISTORY_ENTITY_TYPES))
            raise ValueError(f"entity_type must be one of: {allowed_values}")
        return value


class StatusHistoryCreate(StatusHistoryBase):
    pass


class StatusHistoryRead(StatusHistoryBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class AuditEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    entity_type: str = Field(min_length=1, max_length=64)
    entity_id: uuid.UUID
    actor_id: uuid.UUID
    changed_fields: list[str] = Field(default_factory=list, max_length=32)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("event_type", "entity_type")
    @classmethod
    def normalize_catalog_value(cls, value: str) -> str:
        return value.upper()

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if value not in ADMINISTRATIVE_EVENT_TYPES:
            raise ValueError("unsupported administrative audit event")
        return value

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, value: str) -> str:
        if value not in {"USER", *RECORD_ENTITY_TYPES}:
            raise ValueError("unsupported administrative audit entity")
        return value

    @field_validator("changed_fields")
    @classmethod
    def normalize_changed_fields(cls, value: list[str]) -> list[str]:
        normalized = sorted({field.strip() for field in value if field.strip()})
        if any("," in field for field in normalized):
            raise ValueError("changed field names must not contain commas")
        if any(len(field) > 64 for field in normalized):
            raise ValueError("changed field names must contain at most 64 characters")
        return normalized


class AuditEntryRead(BaseModel):
    id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_name: str | None
    old_status: str | None
    new_status: str | None
    changed_fields: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
