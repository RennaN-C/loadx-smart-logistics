import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_config_points_to_migrations_folder() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))

    assert config.get_main_option("script_location") == "migrations"


def test_alembic_env_uses_application_metadata() -> None:
    env_file = BACKEND_ROOT / "migrations" / "env.py"
    env_content = env_file.read_text(encoding="utf-8")

    assert "from app.database.base import Base" in env_content
    assert "target_metadata = Base.metadata" in env_content
    assert "from app.modules.orders import models as orders_models" in env_content


def test_alembic_has_current_revision_head() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "20260730_0002"


def test_initial_migration_renders_expected_check_constraint_names() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        check=True,
        text=True,
    )

    assert "CONSTRAINT ck_users__role_allowed" in result.stdout
    assert "CONSTRAINT ck_trucks__dimensions_positive" in result.stdout
    assert "CONSTRAINT ck_products__weight_positive" in result.stdout
    assert "CREATE TABLE orders" in result.stdout
    assert "CREATE TABLE order_items" in result.stdout
    assert "CONSTRAINT ck_orders__status_allowed" in result.stdout
    assert "CONSTRAINT fk_orders__customers" in result.stdout
    assert "CONSTRAINT fk_order_items__products" in result.stdout
    assert "ck_users__ck_users" not in result.stdout
    assert "ck_trucks__ck_trucks" not in result.stdout
    assert "ck_products__ck_products" not in result.stdout
