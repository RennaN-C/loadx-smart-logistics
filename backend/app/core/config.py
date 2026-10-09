import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

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
    whatsapp_provider: Literal["mock", "meta"] = "mock"
    whatsapp_real_enabled: bool = False
    whatsapp_access_token: SecretStr = Field(default=SecretStr(""), repr=False)
    whatsapp_phone_number_id: str = Field(default="", repr=False)
    whatsapp_api_version: str = ""
    whatsapp_country_code: str = ""
    whatsapp_timeout_seconds: float = Field(
        default=5.0, ge=0.1, le=30, allow_inf_nan=False
    )
    whatsapp_max_attempts: int = Field(default=2, ge=1, le=3)
    whatsapp_retry_backoff_seconds: float = Field(
        default=0.25, ge=0, le=2, allow_inf_nan=False
    )
    operational_log_level: Literal["INFO", "WARNING", "ERROR"] = "INFO"
    operational_request_logs: bool = True
    evidence_storage_dir: Path | None = None

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

    @field_validator("password_blocklist_path", mode="before")
    @classmethod
    def normalize_optional_blocklist_path(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def reject_insecure_production_defaults(self) -> "Settings":
        if (
            self.password_blocklist_path is not None
            and not self.password_blocklist_path.is_file()
        ):
            raise ValueError("PASSWORD_BLOCKLIST_PATH must point to a readable file.")
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
