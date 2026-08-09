from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
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
    ai_provider: str = "mock"
    whatsapp_provider: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def reject_insecure_production_defaults(self) -> "Settings":
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
    return Settings()


settings = get_settings()
