import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.users.password_policy import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    validate_password_policy,
)
from app.modules.users.schemas import EMAIL_PATTERN, normalize_email


class AuthLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value: str) -> str:
        normalized_value = normalize_email(value)
        if normalized_value is None:
            raise ValueError("email is required")
        return normalized_value


class OwnProfileUpdate(BaseModel):
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    second_factor: str | None = Field(default=None, min_length=6, max_length=64)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255, pattern=EMAIL_PATTERN)

    @field_validator("email")
    @classmethod
    def normalize_own_email(cls, value: str) -> str:
        return value.lower()


class OwnPasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_policy(value)


class OwnSessionRead(BaseModel):
    id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    current: bool


class RecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    email: str = Field(min_length=3, max_length=255, pattern=EMAIL_PATTERN)

    @field_validator("email")
    @classmethod
    def normalize(cls, value: str) -> str:
        return value.lower()


class RecoveryConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=128)
    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )

    @field_validator("new_password")
    @classmethod
    def policy(cls, value: str) -> str:
        return validate_password_policy(value)


class MfaChallengeRead(BaseModel):
    challenge_token: str
    purpose: str
    expires_at: datetime


class MfaChallengeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_token: str = Field(min_length=1, max_length=128)


class MfaVerify(MfaChallengeInput):
    code: str = Field(min_length=6, max_length=64)


class MfaReauth(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=128)
    code: str = Field(default="", max_length=64)


class MfaStatusRead(BaseModel):
    enabled: bool
    required: bool


class MfaProvisionRead(BaseModel):
    provisioning_uri: str


class RecoveryCodesRead(BaseModel):
    recovery_codes: list[str]
