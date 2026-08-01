import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    document: str = Field(min_length=1, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=2, max_length=2)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        return value.upper()


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    document: str | None = Field(default=None, min_length=1, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("name", "document", "address", "city", "state", mode="before")
    @classmethod
    def reject_null_required_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("field must not be null")
        return value

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()


class CustomerRead(CustomerBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
