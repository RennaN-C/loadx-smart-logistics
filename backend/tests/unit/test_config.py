from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("app_env", ["local", "production"])
def test_database_url_is_required(app_env: str, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(app_env=app_env, _env_file=None)


def test_database_url_reads_environment(monkeypatch) -> None:
    database_url = "postgresql+psycopg://localhost/from_environment"
    monkeypatch.setenv("DATABASE_URL", database_url)

    assert Settings(app_env="local", _env_file=None).database_url == database_url


def test_database_url_reads_dotenv(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = "postgresql+psycopg://localhost/from_dotenv"
    env_file = tmp_path / ".env"
    env_file.write_text(f"DATABASE_URL={database_url}\n", encoding="utf-8")

    assert Settings(app_env="local", _env_file=env_file).database_url == database_url


@pytest.mark.parametrize("app_env", ["local", "production"])
@pytest.mark.parametrize(
    "database_url",
    ["", "not-a-url", "sqlite:///local.db", "postgresql+psycopg://localhost"],
)
def test_database_url_rejects_invalid_configuration(
    app_env: str, database_url: str
) -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(app_env=app_env, database_url=database_url, _env_file=None)


def test_ai_explanation_timeout_defaults_to_five_seconds() -> None:
    configured = Settings(app_env="local", _env_file=None)

    assert configured.ai_explanation_timeout_seconds == 5.0


def test_ai_explanation_timeout_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("AI_EXPLANATION_TIMEOUT_SECONDS", "2.5")

    configured = Settings(app_env="local", _env_file=None)

    assert configured.ai_explanation_timeout_seconds == 2.5


@pytest.mark.parametrize("timeout_seconds", [0, -1])
def test_ai_explanation_timeout_must_be_positive(timeout_seconds: int) -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="local",
            ai_explanation_timeout_seconds=timeout_seconds,
            _env_file=None,
        )


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
