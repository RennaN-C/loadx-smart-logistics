import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = "postgresql+psycopg://loadx:loadx_local@db:5432/loadx"
INSECURE_SECRET_KEYS = frozenset(
    {
        "local-only",
        "troque-esta-chave-no-env-local",
    }
)


class Settings(BaseSettings):
    app_env: Literal["local", "production"] = "production"
    database_url: str = LOCAL_DATABASE_URL
    backend_cors_origins_raw: str = Field(
        default="http://localhost:5173", validation_alias="BACKEND_CORS_ORIGINS"
    )
    secret_key: str = "local-only"
    password_blocklist_path: Path | None = None
    ai_provider: str = "mock"
    whatsapp_provider: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

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
        if self.database_url == LOCAL_DATABASE_URL:
            raise ValueError(
                "DATABASE_URL must be explicitly configured in production."
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
