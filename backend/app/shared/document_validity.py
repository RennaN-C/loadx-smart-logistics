from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from pydantic import BaseModel, field_validator, model_validator

DocumentStatus = Literal["VALID", "EXPIRING", "EXPIRED", "NOT_YET_VALID", "SUPERSEDED"]


class DatedDocument(Protocol):
    issued_at: datetime | None
    expires_at: datetime | None
    superseded_at: datetime | None


def utc_datetime(value: datetime | None) -> datetime | None:
    if value is not None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must include timezone")
        return value.astimezone(UTC)
    return None


class DocumentDates(BaseModel):
    issued_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator("issued_at", "expires_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        return utc_datetime(value)

    @model_validator(mode="after")
    def validate_period(self) -> "DocumentDates":
        if (
            self.issued_at is not None
            and self.expires_at is not None
            and self.expires_at <= self.issued_at
        ):
            raise ValueError("expires_at must be after issued_at")
        return self


def document_status(
    record: DatedDocument, *, at: datetime | None = None
) -> DocumentStatus:
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
