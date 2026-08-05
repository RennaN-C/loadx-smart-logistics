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


@pytest.mark.parametrize("path", API_DOCUMENTATION_PATHS)
def test_api_documentation_is_available_in_local_environment(path: str) -> None:
    local_app = create_app(Settings(app_env="local", _env_file=None))

    with TestClient(local_app) as client:
        response = client.get(path)

    assert response.status_code == 200


@pytest.mark.parametrize("path", API_DOCUMENTATION_PATHS)
def test_api_documentation_is_not_exposed_in_production(path: str) -> None:
    production_app = create_app(Settings(app_env="production", _env_file=None))

    with TestClient(production_app) as client:
        response = client.get(path)

    assert response.status_code == 404


def test_production_application_keeps_health_endpoint_available() -> None:
    production_app = create_app(Settings(app_env="production", _env_file=None))

    with TestClient(production_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_settings_reject_unknown_application_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="staging", _env_file=None)


def test_settings_disable_api_documentation_by_default(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)

    assert Settings(_env_file=None).app_env == "production"


def test_settings_read_application_environment_from_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")

    assert Settings(_env_file=None).app_env == "local"
