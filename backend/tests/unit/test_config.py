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
