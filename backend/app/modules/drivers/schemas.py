import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.drivers.document_schemas import LICENSE_CATEGORIES
from app.shared.document_validity import utc_datetime
from app.shared.validators import CNH, CPF, PhoneNumber


class DriverBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    document: str = Field(min_length=1, max_length=32)
    phone: str = Field(min_length=1, max_length=32)
    license_number: str = Field(min_length=1, max_length=32)
    license_expires_at: datetime | None = None
    license_category: str | None = Field(default=None, min_length=1, max_length=8)
    active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("license_expires_at")
    @classmethod
    def validate_expiry(cls, value: datetime | None) -> datetime | None:
        return utc_datetime(value)

    @field_validator("license_category")
    @classmethod
    def normalize_license_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()


class DriverCreate(DriverBase):
    document: CPF = Field(min_length=1, max_length=32)
    phone: PhoneNumber = Field(min_length=1, max_length=32)
    license_number: CNH = Field(min_length=1, max_length=32)


    @field_validator("license_category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is not None and value not in LICENSE_CATEGORIES:
            raise ValueError("license_category must use the current operational catalog")
        return value


class DriverUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    document: CPF | None = Field(default=None, min_length=1, max_length=32)
    phone: PhoneNumber | None = Field(default=None, min_length=1, max_length=32)
    license_number: CNH | None = Field(default=None, min_length=1, max_length=32)
    license_expires_at: datetime | None = None
    license_category: str | None = Field(default=None, min_length=1, max_length=8)
    active: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "name",
        "document",
        "phone",
        "license_number",
        "active",
        mode="before",
    )
    @classmethod
    def reject_null_required_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("field must not be null")
        return value

    @field_validator("license_expires_at")
    @classmethod
    def validate_expiry(cls, value: datetime | None) -> datetime | None:
        return utc_datetime(value)

    @field_validator("license_category")
    @classmethod
    def normalize_license_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.upper()
        if value not in LICENSE_CATEGORIES:
            raise ValueError("license_category must use the current operational catalog")
        return value


class DriverRead(DriverBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class DriverOperationalStatusRead(BaseModel):
    id: uuid.UUID
    name: str
    license_category: str | None
    active: bool
    has_document_conflict: bool
    has_operation_conflict: bool
    available: bool

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class DriverListRead(BaseModel):
    id: uuid.UUID
    name: str
    license_category: str | None
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
