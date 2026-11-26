"""Tenant boundaries for multi-truck distributions in PostgreSQL 16."""

import uuid
from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.modules.load_planning.distribution_repository import LoadDistributionRepository
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID
from tests.integration.test_load_distributions import distribution_scenario
from tests.integration.test_tenancy_g05c import foreign_optimization

__all__ = ("distribution_scenario", "foreign_optimization")


def test_distribution_reads_use_the_session_organization(foreign_optimization):
    scenario, other_id, _, foreign_id = foreign_optimization
    local_id = uuid.UUID(scenario.create()["id"])
    response = scenario.client.get(
        f"/api/v1/load-distributions/{foreign_id}",
        headers=scenario.user.headers,
    )
    assert response.status_code == 404
    assert str(foreign_id) not in response.text

    with scenario.factory() as db:
        local = LoadDistributionRepository(db, LEGACY_ORGANIZATION_ID)
        other = LoadDistributionRepository(db, other_id)
        foreign = other.get(foreign_id)
        part = foreign.parts[0]
        order = foreign.orders[0]
        assert local.get(local_id).organization_id == LEGACY_ORGANIZATION_ID
        assert local.get(foreign_id) is None
        assert other.get(local_id) is None
        assert local.plan_part(part.load_plan_id) is None
        assert other.plan_part(part.load_plan_id).id == part.id
        assert not local.has_active_orders([order.order_id])
        assert other.has_active_orders([order.order_id])
        assert local.order_parts(part.id, order.order_id) is None
        assert other.order_parts(part.id, order.order_id) == (foreign_id, (part.id,))


def test_downgrade_preserves_distribution_from_another_org(foreign_optimization):
    scenario, other_id, _, foreign_id = foreign_optimization
    migration = import_module(
        "migrations.versions.20261119_0046_scope_load_distributions"
    )
    with scenario.factory() as db:
        with (
            pytest.raises(DBAPIError, match="G06-A downgrade refused"),
            db.begin_nested(),
            Operations.context(MigrationContext.configure(db.connection())),
        ):
            migration.downgrade()
        assert LoadDistributionRepository(db, other_id).get(foreign_id) is not None


def test_legacy_distribution_survives_migration_round_trip(distribution_scenario):
    scenario = distribution_scenario
    created = scenario.create()
    identifier = uuid.UUID(created["id"])
    migration = import_module(
        "migrations.versions.20261119_0046_scope_load_distributions"
    )
    with scenario.factory() as db:
        with Operations.context(MigrationContext.configure(db.connection())):
            migration.downgrade()
            assert (
                db.scalar(
                    text("SELECT status FROM load_distributions WHERE id=:id"),
                    {"id": identifier},
                )
                == created["status"]
            )
            migration.upgrade()
        restored = LoadDistributionRepository(db).get(identifier)
        assert {str(part.id) for part in restored.parts} == {
            part["id"] for part in created["parts"]
        }
        assert {(str(v.order_item_id), v.volume_index) for v in restored.volumes} == {
            (v["order_item_id"], v["volume_index"]) for v in created["volumes"]
        }
        assert restored.organization_id == LEGACY_ORGANIZATION_ID
