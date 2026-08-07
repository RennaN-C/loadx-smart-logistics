import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app

API_DOCUMENTATION_PATHS = (
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/openapi.json",
)
PRODUCTION_DATABASE_URL = (
    "postgresql+psycopg://loadx_app:production-password@postgres:5432/loadx"
)
PRODUCTION_SECRET_KEY = "production-test-secret-key-with-32-characters"


def production_settings() -> Settings:
    return Settings(
        app_env="production",
        database_url=PRODUCTION_DATABASE_URL,
        secret_key=PRODUCTION_SECRET_KEY,
        _env_file=None,
    )


@pytest.mark.parametrize("path", API_DOCUMENTATION_PATHS)
def test_api_documentation_is_available_in_local_environment(path: str) -> None:
    local_app = create_app(Settings(app_env="local", _env_file=None))

    with TestClient(local_app) as client:
        response = client.get(path)

    assert response.status_code == 200


@pytest.mark.parametrize("path", API_DOCUMENTATION_PATHS)
def test_api_documentation_is_not_exposed_in_production(path: str) -> None:
    production_app = create_app(production_settings())

    with TestClient(production_app) as client:
        response = client.get(path)

    assert response.status_code == 404


def test_production_application_keeps_health_endpoint_available() -> None:
    production_app = create_app(production_settings())

    with TestClient(production_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_settings_reject_unknown_application_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="staging", _env_file=None)


def test_settings_disable_api_documentation_by_default(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)

    assert (
        Settings(
            database_url=PRODUCTION_DATABASE_URL,
            secret_key=PRODUCTION_SECRET_KEY,
            _env_file=None,
        ).app_env
        == "production"
    )


def test_settings_read_application_environment_from_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")

    assert Settings(_env_file=None).app_env == "local"


@pytest.mark.parametrize(
    ("overrides", "expected_message"),
    [
        ({"secret_key": "local-only"}, "SECRET_KEY"),
        (
            {"database_url": ("postgresql+psycopg://loadx:loadx_local@db:5432/loadx")},
            "DATABASE_URL",
        ),
        ({"backend_cors_origins_raw": "*"}, "Wildcard CORS"),
    ],
)
def test_settings_reject_insecure_production_configuration(
    overrides: dict[str, str], expected_message: str
) -> None:
    values = {
        "app_env": "production",
        "database_url": PRODUCTION_DATABASE_URL,
        "secret_key": PRODUCTION_SECRET_KEY,
        "_env_file": None,
    }
    values.update(overrides)

    with pytest.raises(ValidationError, match=expected_message):
        Settings(**values)


@pytest.mark.parametrize("minutes", [0, 1_441])
def test_settings_reject_invalid_token_expiration(minutes: int) -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="local", access_token_expire_minutes=minutes, _env_file=None)


def test_settings_reject_unsupported_jwt_algorithm() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="local", jwt_algorithm="none", _env_file=None)
