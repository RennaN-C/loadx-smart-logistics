import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DriverBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    document: str = Field(min_length=1, max_length=32)
    phone: str = Field(min_length=1, max_length=32)
    license_number: str = Field(min_length=1, max_length=32)
    license_category: str | None = Field(default=None, min_length=1, max_length=8)
    active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("license_category")
    @classmethod
    def normalize_license_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()


class DriverCreate(DriverBase):
    pass


class DriverUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    document: str | None = Field(default=None, min_length=1, max_length=32)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    license_number: str | None = Field(default=None, min_length=1, max_length=32)
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

    @field_validator("license_category")
    @classmethod
    def normalize_license_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()


class DriverRead(DriverBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class DriverListRead(BaseModel):
    id: uuid.UUID
    name: str
    license_category: str | None
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
