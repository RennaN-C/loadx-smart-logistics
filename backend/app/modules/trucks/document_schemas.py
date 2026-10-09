import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.trucks.maintenance_schemas import utc_datetime
from app.modules.trucks.models import TruckDocument

DocumentKind = Literal["CRLV", "LICENSING", "INSURANCE"]
DocumentStatus = Literal["VALID", "EXPIRING", "EXPIRED", "NOT_YET_VALID", "SUPERSEDED"]


class DocumentCreate(BaseModel):
    kind: DocumentKind
    reference: str = Field(min_length=1, max_length=120)
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    file_reference: uuid.UUID | None = None
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("issued_at", "expires_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        return utc_datetime(value)

    @model_validator(mode="after")
    def validate_period(self) -> "DocumentCreate":
        if (
            self.issued_at is not None
            and self.expires_at is not None
            and self.expires_at <= self.issued_at
        ):
            raise ValueError("expires_at must be after issued_at")
        return self


class DocumentRead(DocumentCreate):
    id: uuid.UUID
    truck_id: uuid.UUID
    superseded_at: datetime | None
    created_at: datetime
    status: DocumentStatus
    model_config = ConfigDict(from_attributes=True)


class PolicyUpdate(BaseModel):
    required: bool = Field(strict=True)
    model_config = ConfigDict(extra="forbid")


class PolicyRead(PolicyUpdate):
    id: uuid.UUID
    truck_id: uuid.UUID
    kind: DocumentKind
    model_config = ConfigDict(from_attributes=True)


def document_status(record: TruckDocument, *, at: datetime | None = None) -> DocumentStatus:
    now = at or datetime.now(UTC)
    if record.superseded_at is not None:
        return "SUPERSEDED"
    if record.expires_at is not None and record.expires_at <= now:
        return "EXPIRED"
    if record.issued_at is not None and record.issued_at > now:
        return "NOT_YET_VALID"
    if record.expires_at is not None and record.expires_at <= now + timedelta(days=30):
        return "EXPIRING"
    return "VALID"
