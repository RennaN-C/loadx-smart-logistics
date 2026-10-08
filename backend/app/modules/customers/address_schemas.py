import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_postal_code(value: str | None) -> str | None:
    if value is None:
        return None
    if not re.fullmatch(r"[0-9]{5}-?[0-9]{3}", value):
        raise ValueError("postal_code must contain 8 digits")
    return value.replace("-", "")


class CustomerAddressCreate(BaseModel):
    label: str = Field(default="Principal", min_length=1, max_length=80)
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=2, max_length=2)
    postal_code: str | None = None
    active: bool = True
    is_primary: bool = False

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("state")
    @classmethod
    def uppercase_state(cls, value: str) -> str:
        return value.upper()

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str | None) -> str | None:
        return normalize_postal_code(value)


class CustomerAddressUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    postal_code: str | None = None
    active: bool | None = None
    is_primary: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator(
        "label", "address", "city", "state", "active", "is_primary", mode="before"
    )
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("field must not be null")
        return value

    @field_validator("state")
    @classmethod
    def uppercase_state(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str | None) -> str | None:
        return normalize_postal_code(value)


class CustomerAddressRead(CustomerAddressCreate):
    id: uuid.UUID
    customer_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
