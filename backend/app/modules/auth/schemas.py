from pydantic import BaseModel, Field, field_validator

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
