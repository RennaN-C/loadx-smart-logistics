import uuid
from datetime import UTC, datetime
from re import fullmatch
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

OCCURRENCE_TYPE_VALUES = (
    "DAMAGED_PRODUCT",
    "CUSTOMER_ABSENT",
    "WRONG_ADDRESS",
    "REFUSED_PRODUCT",
    "MISSING_VOLUME",
    "DELAY",
    "VEHICLE_PROBLEM",
    "LOADING_PROBLEM",
)


class OccurrenceCreate(BaseModel):
    trip_id: uuid.UUID
    delivery_id: uuid.UUID | None = None
    type: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1)
    photo_url: str | None = Field(default=None, max_length=2048)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in OCCURRENCE_TYPE_VALUES:
            raise ValueError("type must be a supported occurrence type")
        return normalized

    @field_validator("photo_url")
    @classmethod
    def validate_photo_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        identifier = parsed.path.removeprefix("/")
        if (
            parsed.scheme != "mock"
            or parsed.netloc != "occurrences"
            or not parsed.path.startswith("/")
            or fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", identifier) is None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("photo_url must use mock://occurrences/<identifier>")
        return value


class OccurrenceRead(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    delivery_id: uuid.UUID | None
    type: str
    description: str
    photo_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
