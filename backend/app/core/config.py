from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://loadx:loadx_local@db:5432/loadx"
    backend_cors_origins_raw: str = Field(default="http://localhost:5173", validation_alias="BACKEND_CORS_ORIGINS")
    secret_key: str = "local-only"
    ai_provider: str = "mock"
    whatsapp_provider: str = "mock"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def backend_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
