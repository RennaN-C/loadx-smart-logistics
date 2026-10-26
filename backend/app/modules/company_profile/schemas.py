import re
import uuid
from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.users.schemas import EMAIL_PATTERN
from app.shared.validators import normalize_cnpj, normalize_phone


class CompanyProfileInput(BaseModel):
    legal_name: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=160)
    cnpj: str | None = Field(default=None, max_length=18)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    logo_reference: str | None = Field(default=None, max_length=2048)
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("cnpj", "phone", "email", "logo_reference", mode="before")
    @classmethod
    def empty_optional(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("cnpj")
    @classmethod
    def cnpj_valid(cls, value: str | None) -> str | None:
        return normalize_cnpj(value) if value is not None else None

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value is not None else None

    @field_validator("email")
    @classmethod
    def email_valid(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(EMAIL_PATTERN, value) is None:
            raise ValueError("Informe um e-mail válido.")
        return value.lower() if value is not None else None

    @field_validator("logo_reference")
    @classmethod
    def logo_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as exc:
            raise ValueError(
                "Informe uma referência HTTPS válida para o logotipo."
            ) from exc
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or any(c.isspace() or ord(c) < 32 for c in value)
            or port == 0
        ):
            raise ValueError(
                "Informe uma referência HTTPS sem credenciais para o logotipo."
            )
        return value


class CompanyProfileRead(CompanyProfileInput):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
