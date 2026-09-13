import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.validators import CustomerDocument, PhoneNumber


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
    document: CustomerDocument = Field(min_length=1, max_length=32)
    phone: PhoneNumber | None = Field(default=None, max_length=32)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    document: CustomerDocument | None = Field(default=None, min_length=1, max_length=32)
    phone: PhoneNumber | None = Field(default=None, max_length=32)
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


class CustomerListRead(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    state: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
