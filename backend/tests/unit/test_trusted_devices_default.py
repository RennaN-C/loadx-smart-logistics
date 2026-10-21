"""Trusted-device availability must not opt in a browser automatically."""

from app.core.config import Settings

DATABASE_URL = "postgresql+psycopg://loadx:test@localhost:5432/loadx"


def test_trusted_devices_available_by_default(monkeypatch):
    monkeypatch.delenv("TRUSTED_DEVICES_ENABLED", raising=False)
    config = Settings(
        database_url=DATABASE_URL,
        app_env="local",
        _env_file=None,
    )
    assert config.trusted_devices_enabled is True
    assert config.trusted_device_days == 30


def test_trusted_devices_can_be_disabled_by_environment(monkeypatch):
    monkeypatch.setenv("TRUSTED_DEVICES_ENABLED", "false")
    config = Settings(
        database_url=DATABASE_URL,
        app_env="local",
        _env_file=None,
    )
    assert config.trusted_devices_enabled is False
