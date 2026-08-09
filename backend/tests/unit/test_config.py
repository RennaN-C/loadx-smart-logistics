from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_empty_password_blocklist_path() -> None:
    configured = Settings(
        app_env="local",
        password_blocklist_path="",
        _env_file=None,
    )

    assert configured.password_blocklist_path is None


def test_settings_accept_existing_password_blocklist_path(tmp_path: Path) -> None:
    blocklist_path = tmp_path / "passwords.txt"
    blocklist_path.write_text("compromised password\n", encoding="utf-8")

    configured = Settings(
        app_env="local",
        password_blocklist_path=blocklist_path,
        _env_file=None,
    )

    assert configured.password_blocklist_path == blocklist_path


def test_settings_reject_missing_password_blocklist_path(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="PASSWORD_BLOCKLIST_PATH"):
        Settings(
            app_env="local",
            password_blocklist_path=tmp_path / "missing.txt",
            _env_file=None,
        )


def test_settings_load_production_credentials_from_secret_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / "SECRET_KEY").write_text(
        "production-secret-key-with-more-than-32-characters",
        encoding="utf-8",
    )
    (tmp_path / "DATABASE_URL").write_text(
        "postgresql+psycopg://loadx_app:secret@db:5432/loadx",
        encoding="utf-8",
    )

    configured = Settings(
        app_env="production",
        backend_cors_origins_raw="https://loadx.example.test",
        _env_file=None,
        _secrets_dir=tmp_path,
    )

    assert configured.secret_key.startswith("production-secret-key")
    assert "loadx_app" in configured.database_url
