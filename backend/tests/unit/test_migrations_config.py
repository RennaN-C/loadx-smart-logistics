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
    assert (
        "from app.modules.load_planning import models as load_planning_models"
        in env_content
    )
    assert "from app.modules.orders import models as orders_models" in env_content


def test_alembic_has_current_revision_head() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["20261009_0020"]
    assert script.get_revision("20261009_0020").down_revision == "20261009_0019"
    assert script.get_revision("20261009_0019").down_revision == "20261009_0018"
    assert script.get_revision("20261009_0018").down_revision == "20261008_0017"
    assert script.get_revision("20261006_0012").down_revision == "20260830_0011"


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
    assert "CREATE TABLE status_history" in result.stdout
    assert "CONSTRAINT fk_status_history__users" in result.stdout
    assert "CREATE INDEX ix_status_history__entity" in result.stdout
    assert "CREATE TABLE audit_events" in result.stdout
    assert "CONSTRAINT fk_audit_events__users" in result.stdout
    assert "CONSTRAINT ck_audit_events__event_type_allowed" in result.stdout
    assert "CONSTRAINT ck_audit_events__entity_type_allowed" in result.stdout
    assert "CREATE INDEX ix_audit_events__entity" in result.stdout
    assert "CREATE INDEX ix_audit_events__actor_id" in result.stdout
    assert "CREATE INDEX ix_audit_events__created_at" in result.stdout
    assert "CREATE TABLE load_plans" in result.stdout
    assert "CREATE TABLE load_plan_orders" in result.stdout
    assert "CREATE TABLE load_plan_items" in result.stdout
    assert "CONSTRAINT ck_load_plans__status_allowed" in result.stdout
    assert "CONSTRAINT ck_load_plans__approval_consistent" in result.stdout
    assert "CONSTRAINT ck_load_plan_items__placed_or_rejected" in result.stdout
    assert "CONSTRAINT ck_load_plan_items__rotation_code_allowed" in result.stdout
    assert (
        "CONSTRAINT ck_load_plan_items__rotation_permission_consistent" in result.stdout
    )
    assert "CONSTRAINT ck_load_plan_items__rejection_reason_allowed" in result.stdout
    assert "CONSTRAINT fk_load_plan_items__order_items" in result.stdout
    assert "CONSTRAINT fk_load_plan_items__load_plan_orders" in result.stdout
    assert "CONSTRAINT fk_load_plan_items__order_item_provenance" in result.stdout
    assert "CONSTRAINT uq_order_items__id_order_product" in result.stdout
    assert "CONSTRAINT uq_load_plan_items__plan_item_volume" in result.stdout
    assert "CREATE TABLE auth_login_throttles" in result.stdout
    assert "CONSTRAINT ck_auth_login_throttles__scope_allowed" in result.stdout
    assert "CREATE TABLE auth_sessions" in result.stdout
    assert "CREATE TABLE external_commands" in result.stdout
    assert "uq_external_commands__integration_id_event_hash" in result.stdout
    assert "CONSTRAINT fk_auth_sessions__users" in result.stdout
    assert "CONSTRAINT uq_auth_sessions__token_hash" in result.stdout
    assert "ck_users__ck_users" not in result.stdout
    assert "ck_trucks__ck_trucks" not in result.stdout
    assert "ck_products__ck_products" not in result.stdout
