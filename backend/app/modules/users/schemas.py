import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.users.password_policy import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    validate_password_policy,
)

USER_ROLE_VALUES = {"ADMIN", "CHECKER", "DRIVER", "LOGISTICS_MANAGER"}
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower()


def normalize_role(value: str | None) -> str | None:
    if value is None:
        return None
    normalized_value = value.strip().upper()
    if normalized_value not in USER_ROLE_VALUES:
        allowed_values = ", ".join(sorted(USER_ROLE_VALUES))
        raise ValueError(f"role must be one of: {allowed_values}")
    return normalized_value


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255, pattern=EMAIL_PATTERN)
    role: str = Field(min_length=1, max_length=32)
    active: bool = True
    driver_id: uuid.UUID | None = None

    model_config = ConfigDict()

    @field_validator("name", mode="before")
    @classmethod
    def normalize_user_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalize_user_email(cls, value: str) -> str:
        normalized_value = normalize_email(value)
        if normalized_value is None:
            raise ValueError("email is required")
        return normalized_value

    @field_validator("role")
    @classmethod
    def normalize_user_role(cls, value: str) -> str:
        normalized_value = normalize_role(value)
        if normalized_value is None:
            raise ValueError("role is required")
        return normalized_value


class UserCreate(UserBase):
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("password")
    @classmethod
    def validate_user_password(cls, value: str) -> str:
        return validate_password_policy(value)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(
        default=None, min_length=3, max_length=255, pattern=EMAIL_PATTERN
    )
    password: str | None = Field(
        default=None,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    role: str | None = Field(default=None, min_length=1, max_length=32)
    active: bool | None = None
    driver_id: uuid.UUID | None = None

    model_config = ConfigDict()

    @field_validator("name", "email", "password", "role", "active", mode="before")
    @classmethod
    def reject_null_required_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("field must not be null")
        return value

    @field_validator("email")
    @classmethod
    def normalize_user_email(cls, value: str | None) -> str | None:
        return normalize_email(value)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_user_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_user_password(cls, value: str | None) -> str | None:
        return validate_password_policy(value) if value is not None else None

    @field_validator("role")
    @classmethod
    def normalize_user_role(cls, value: str | None) -> str | None:
        return normalize_role(value)


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class UserListRead(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
