import os
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import (
    Field,
    Json,
    SecretBytes,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.modules.external_commands.schemas import CommandName

INSECURE_SECRET_KEYS = frozenset(
    {
        "local-only",
        "troque-esta-chave-no-env-local",
    }
)


class Settings(BaseSettings):
    app_env: Literal["local", "production"] = "production"
    database_url: str
    backend_cors_origins_raw: str = Field(
        default="http://localhost:5173", validation_alias="BACKEND_CORS_ORIGINS"
    )
    secret_key: str = "local-only"
    password_blocklist_path: Path | None = None
    ai_provider: str = "mock"
    ai_explanation_timeout_seconds: float = Field(default=5.0, gt=0)
    whatsapp_provider: Literal["mock"] = "mock"
    outbox_lease_seconds: int = Field(default=60, ge=10, le=600)
    outbox_max_attempts: int = Field(default=5, ge=1, le=20)
    outbox_base_seconds: int = Field(default=30, ge=1, le=3600)
    outbox_cap_seconds: int = Field(default=3600, ge=1, le=86400)
    outbox_poll_seconds: float = Field(default=2, ge=0.1, le=60)
    operational_log_level: Literal["INFO", "WARNING", "ERROR"] = "INFO"
    operational_request_logs: bool = True
    evidence_storage_dir: Path | None = None
    trusted_devices_enabled: bool = False
    trusted_device_days: int = Field(default=30, ge=1, le=30)
    mfa_encryption_key: SecretStr | None = None
    password_recovery_provider: Literal["none", "smtp"] = "none"
    password_recovery_url: str | None = None
    smtp_security: Literal["ssl", "starttls", "local"] = "ssl"
    smtp_host: str | None = None
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_sender: str | None = None
    inbound_webhook_enabled: bool = False
    inbound_webhook_signing_key: SecretBytes | None = Field(default=None, repr=False)
    inbound_webhook_bindings: Json[dict[str, uuid.UUID]] = Field(
        default="{}", repr=False
    )
    inbound_webhook_capabilities: Json[list[CommandName]] = Field(default="[]")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        try:
            url = make_url(value)
        except (ArgumentError, ValueError):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL.") from None
        if url.drivername != "postgresql+psycopg" or not url.database:
            raise ValueError(
                "DATABASE_URL must use postgresql+psycopg and name a database."
            )
        return value

    @field_validator("mfa_encryption_key", "smtp_password", mode="before")
    @classmethod
    def optional_secret(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("password_blocklist_path", mode="before")
    @classmethod
    def normalize_optional_blocklist_path(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_inbound_webhook(self) -> "Settings":
        key = self.inbound_webhook_signing_key
        if key is not None and (
            len(key.get_secret_value()) < 32
            or key.get_secret_value() == self.secret_key.encode()
        ):
            raise ValueError(
                "Inbound signing key must be exclusive and at least 32 bytes."
            )
        if any(
            re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", subject) is None
            for subject in self.inbound_webhook_bindings
        ):
            raise ValueError("Invalid configured inbound subject binding.")
        if self.inbound_webhook_enabled and (
            key is None
            or not self.inbound_webhook_bindings
            or not self.inbound_webhook_capabilities
        ):
            raise ValueError(
                "Enabled inbound webhook requires key, bindings and capabilities."
            )
        return self

    @model_validator(mode="after")
    def reject_insecure_production_defaults(self) -> "Settings":
        if (
            self.password_blocklist_path is not None
            and not self.password_blocklist_path.is_file()
        ):
            raise ValueError("PASSWORD_BLOCKLIST_PATH must point to a readable file.")
        if self.mfa_encryption_key is not None:
            from cryptography.fernet import Fernet

            try:
                Fernet(self.mfa_encryption_key.get_secret_value().encode("ascii"))
            except ValueError:
                raise ValueError(
                    "MFA_ENCRYPTION_KEY must be a valid Fernet key."
                ) from None
            if self.mfa_encryption_key.get_secret_value() == self.secret_key:
                raise ValueError("MFA encryption requires a dedicated key.")
        if self.app_env != "production":
            return self
        if len(self.secret_key) < 32 or self.secret_key in INSECURE_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY must be unique and contain at least 32 characters "
                "in production."
            )
        if "*" in self.backend_cors_origins:
            raise ValueError("Wildcard CORS origins are forbidden in production.")
        return self

    @property
    def backend_cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def trusted_device_cookie_name(self) -> str:
        return (
            "__Host-loadx_trusted_device"
            if self.app_env == "production"
            else "loadx_trusted_device"
        )

    @property
    def session_cookie_name(self) -> str:
        if self.app_env == "production":
            return "__Host-loadx_session"
        return "loadx_session"

    @property
    def session_cookie_secure(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    raw_secrets_dir = os.getenv("LOADX_SECRETS_DIR", "").strip()
    secrets_dir = Path(raw_secrets_dir) if raw_secrets_dir else None
    if secrets_dir is not None and not secrets_dir.is_dir():
        raise ValueError("LOADX_SECRETS_DIR must point to a readable directory.")
    return Settings(_secrets_dir=secrets_dir)


settings = get_settings()
