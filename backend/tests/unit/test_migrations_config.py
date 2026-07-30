from pathlib import Path

from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_config_points_to_migrations_folder() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))

    assert config.get_main_option("script_location") == "migrations"


def test_alembic_env_uses_application_metadata() -> None:
    env_file = BACKEND_ROOT / "migrations" / "env.py"
    env_content = env_file.read_text(encoding="utf-8")

    assert "from app.database.base import Base" in env_content
    assert "target_metadata = Base.metadata" in env_content
