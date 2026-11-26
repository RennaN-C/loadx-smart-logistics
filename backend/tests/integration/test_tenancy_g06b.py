"""PostgreSQL 16 loading ownership, exact-plan provenance and HTTP isolation."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.modules.load_planning.models import LoadPlanOrder
from app.modules.load_planning.repository import LoadPlanRepository
from app.modules.loading.models import LoadingSession, LoadingSessionItem
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.loading.repository import LoadingRepository
from app.modules.loading.service import (
    LoadingOrganizationNotEnabledError,
    LoadingService,
)
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID
from tests.integration.test_deliveries_api import seed_operational_scenario
from tests.integration.test_loading_authorization import _create_loading, _start_loading
from tests.integration.test_tenancy_g05b import (
    _order_and_item,
    _other_organization,
    _plan,
    _rejected_volume,
    _truck,
)

BASE = "/api/v1/loading-sessions"
MIGRATION = "migrations.versions.20261125_0047_scope_loading_sessions"


@pytest.fixture
def loading_pair(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    local = _create_loading(client, scenario)
    _start_loading(client, scenario, local)
    with session_factory() as db:
        organization = _other_organization(db)
        order, item, product = _order_and_item(db, organization.id)
        order.status = "PLANNED"
        truck = _truck(db, organization.id, "G06B123")
        plan = _plan(organization.id, truck.id)
        plan.status, plan.approved_at = "APPROVED", datetime.now(UTC)
        plan.loaded_count, plan.unloaded_count = 1, 0
        plan.used_volume_cm3, plan.occupancy_percent = 6000, Decimal("0.60")
        plan.total_weight_kg = product.weight_kg
        plan.orders = [LoadPlanOrder(order_id=order.id)]
        volume = _rejected_volume(None, order, item, product)
        volume.placed, volume.rejection_reason = True, None
        volume.position_x_cm = volume.position_y_cm = volume.position_z_cm = 0
        volume.used_width_cm, volume.used_height_cm, volume.used_length_cm = 10, 20, 30
        volume.rotation_code, volume.loading_sequence = "XYZ", 1
        plan.items = [volume]
        LoadPlanRepository(db, organization.id).add(plan)
        db.flush()
        foreign = LoadingSession(
            organization_id=organization.id,
            load_plan_id=plan.id,
            status="IN_PROGRESS",
            started_at=datetime.now(UTC),
            items=[
                LoadingSessionItem(
                    organization_id=organization.id,
                    load_plan_id=plan.id,
                    load_plan_item_id=volume.id,
                    status="PENDING",
                )
            ],
        )
        LoadingRepository(db, organization.id).add(foreign)
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        values = {
            "organization": organization.id,
            "session": foreign.id,
            "plan": plan.id,
            "item": foreign.items[0].id,
            "plan_item": volume.id,
        }
        db.commit()
    return scenario, local, values


def test_repository_and_reference_do_not_reuse_known_foreign_ids(
    loading_pair,
    session_factory,
):
    scenario, local, foreign = loading_pair
    with session_factory() as db:
        b = LoadingRepository(db, foreign["organization"])
        a = LoadingRepository(db, LEGACY_ORGANIZATION_ID)
        cached = b.get(foreign["session"])
        assert cached is not None
        assert b.get_by_load_plan_id(foreign["plan"]).id == cached.id
        assert b.get_item_for_update(foreign["item"]).loading_session_id == cached.id
        assert a.get(foreign["session"]) is None
        assert a.get_for_update(foreign["session"]) is None
        assert a.get_by_load_plan_id(foreign["plan"]) is None
        assert a.get_item_for_update(foreign["item"]) is None
        assert a.get(uuid.UUID(local["id"])).load_plan_id == scenario.load_plan_id
        assert b.get(uuid.UUID(local["id"])) is None
        assert LoadingReferenceService(db).get_by_load_plan_id(foreign["plan"]) is None
        assert not LoadingReferenceService(db).is_load_plan_finished(foreign["plan"])
        projection = LoadingReferenceService.plan_operation_projection()
        assert (
            foreign["plan"] not in db.scalars(select(projection.c.load_plan_id)).all()
        )
        projection_b = LoadingReferenceService.plan_operation_projection(
            foreign["organization"]
        )
        assert foreign["plan"] in db.scalars(select(projection_b.c.load_plan_id)).all()


@pytest.mark.parametrize("operation", ["read", "status", "item", "scan", "create"])
def test_http_foreign_loading_ids_cannot_be_read_or_mutated(
    loading_pair,
    client,
    session_factory,
    operation,
):
    scenario, local, foreign = loading_pair
    headers = {
        **scenario.admin_headers,
        "X-Organization-ID": str(foreign["organization"]),
    }
    params = {"organization_id": str(foreign["organization"])}
    if operation == "read":
        response = client.get(
            BASE + f"/{foreign['session']}", headers=headers, params=params
        )
    elif operation == "status":
        response = client.patch(
            BASE + f"/{foreign['session']}/status",
            headers=headers,
            json={"status": "FINISHED"},
            params=params,
        )
    elif operation == "item":
        response = client.patch(
            BASE + f"/{local['id']}/items/{foreign['item']}",
            headers=headers,
            json={"status": "CHECKED"},
            params=params,
        )
    elif operation == "scan":
        response = client.post(
            BASE + f"/{local['id']}/scan",
            headers=headers,
            json={"code": f"loadx:loading-item:{foreign['item']}"},
            params=params,
        )
    else:
        response = client.post(
            BASE,
            headers=headers,
            json={"load_plan_id": str(foreign["plan"])},
            params=params,
        )
    assert response.status_code == (409 if operation == "create" else 404), (
        response.text
    )
    for value in foreign.values():
        assert str(value) not in response.text
    with session_factory() as db:
        foreign_row = LoadingRepository(db, foreign["organization"]).get(
            foreign["session"]
        )
        assert foreign_row.status == "IN_PROGRESS"
        assert foreign_row.items[0].status == "PENDING"
        assert all(
            row.status == "PENDING"
            for row in LoadingRepository(db).get(uuid.UUID(local["id"])).items
        )


def test_context_comes_from_session_and_full_legacy_checklist_still_completes(
    loading_pair,
    client,
    session_factory,
):
    scenario, local, foreign = loading_pair
    headers = {
        **scenario.admin_headers,
        "X-Organization-ID": str(foreign["organization"]),
    }
    forged = client.post(
        BASE,
        headers=headers,
        json={
            "load_plan_id": str(scenario.load_plan_id),
            "organization_id": str(foreign["organization"]),
        },
    )
    assert forged.status_code == 422
    repeated = client.post(
        BASE, headers=headers, json={"load_plan_id": str(scenario.load_plan_id)}
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == local["id"]
    for item in local["items"]:
        response = client.patch(
            BASE + f"/{local['id']}/items/{item['id']}",
            headers=headers,
            json={"status": "CHECKED"},
        )
        assert response.status_code == 200, response.text
    finished = client.patch(
        BASE + f"/{local['id']}/status",
        headers=headers,
        json={"status": "FINISHED"},
    )
    assert finished.status_code == 200, finished.text
    assert finished.json()["status"] == "FINISHED"
    with session_factory() as db:
        row = LoadingRepository(db).get(uuid.UUID(local["id"]))
        assert row.organization_id == LEGACY_ORGANIZATION_ID
        assert all(
            item.organization_id == row.organization_id
            and item.load_plan_id == row.load_plan_id
            for item in row.items
        )
        assert LoadingReferenceService(db).is_load_plan_finished(scenario.load_plan_id)
        assert not LoadingReferenceService(db).is_load_plan_finished(foreign["plan"])


def test_database_rejects_cross_tenant_item_and_wrong_plan_in_same_tenant(
    loading_pair,
    client,
    session_factory,
):
    scenario, local, foreign = loading_pair
    other = seed_operational_scenario(session_factory)
    other_loading = _create_loading(client, other)
    for plan_item_id in (
        foreign["plan_item"],
        uuid.UUID(other_loading["items"][0]["load_plan_item_id"]),
    ):
        with session_factory() as db:
            with pytest.raises(IntegrityError) as error, db.begin_nested():
                db.add(
                    LoadingSessionItem(
                        organization_id=LEGACY_ORGANIZATION_ID,
                        load_plan_id=scenario.load_plan_id,
                        loading_session_id=uuid.UUID(local["id"]),
                        load_plan_item_id=plan_item_id,
                        status="PENDING",
                    )
                )
                db.flush()
            assert error.value.orig.sqlstate == "23503"
            assert (
                error.value.orig.diag.constraint_name
                == "fk_loading_session_items__org_plan_item"
            )
            assert len(LoadingRepository(db).get(uuid.UUID(local["id"])).items) == len(
                local["items"]
            )


def test_repository_rejects_foreign_graph_and_service_keeps_second_org_disabled(
    loading_pair,
    session_factory,
):
    scenario, _, foreign = loading_pair
    with session_factory() as db:
        forged = LoadingSession(
            organization_id=foreign["organization"],
            load_plan_id=foreign["plan"],
            status="PENDING",
        )
        with pytest.raises(ValueError, match="different organization"):
            LoadingRepository(db).add(forged)
        invalid_child = LoadingSession(
            organization_id=LEGACY_ORGANIZATION_ID,
            load_plan_id=scenario.load_plan_id,
            status="PENDING",
            items=[
                LoadingSessionItem(
                    organization_id=LEGACY_ORGANIZATION_ID,
                    load_plan_id=foreign["plan"],
                    load_plan_item_id=foreign["plan_item"],
                    status="PENDING",
                )
            ],
        )
        with pytest.raises(ValueError, match="different organization or plan"):
            LoadingRepository(db).add(invalid_child)
        with pytest.raises(LoadingOrganizationNotEnabledError):
            LoadingService(db, foreign["organization"])


def test_downgrade_refuses_foreign_loading_without_altering_schema_or_rows(
    loading_pair,
    session_factory,
):
    _, _, foreign = loading_pair
    with session_factory() as db:
        with (
            pytest.raises(DBAPIError, match="G06-B downgrade refused"),
            db.begin_nested(),
            Operations.context(MigrationContext.configure(db.connection())),
        ):
            import_module(MIGRATION).downgrade()
        row = LoadingRepository(db, foreign["organization"]).get(foreign["session"])
        assert row.load_plan_id == foreign["plan"]
        assert row.items[0].id == foreign["item"]
        assert row.items[0].load_plan_id == foreign["plan"]
        assert row.items[0].status == "PENDING"
        for table, required in (
            ("loading_sessions", {"organization_id"}),
            ("loading_session_items", {"organization_id", "load_plan_id"}),
        ):
            columns = {
                column["name"]: column
                for column in inspect(db.connection()).get_columns(table)
            }
            assert required <= columns.keys()
            assert all(
                not columns[name]["nullable"] and columns[name]["default"] is None
                for name in required
            )


def test_migration_round_trip_preserves_finished_loading_and_checked_item_ids(
    client,
    session_factory,
):
    scenario = seed_operational_scenario(session_factory)
    loading = _create_loading(client, scenario)
    _start_loading(client, scenario, loading)
    for item in loading["items"]:
        response = client.patch(
            BASE + f"/{loading['id']}/items/{item['id']}",
            headers=scenario.checker_headers,
            json={"status": "CHECKED"},
        )
        assert response.status_code == 200, response.text
    response = client.patch(
        BASE + f"/{loading['id']}/status",
        headers=scenario.checker_headers,
        json={"status": "FINISHED"},
    )
    assert response.status_code == 200, response.text
    sessions = text(
        "SELECT id,load_plan_id,status,started_at,finished_at FROM loading_sessions ORDER BY id"
    )
    items = text(
        "SELECT id,loading_session_id,load_plan_item_id,status FROM loading_session_items ORDER BY id"
    )
    with session_factory() as db:
        before_sessions = db.execute(sessions).all()
        before_items = db.execute(items).all()
        # Fixture commits release savepoints, while physical-plan triggers wait
        # for the outer transaction. Validate those events before DDL touches
        # the referenced plan-items table, as a committed deployment would.
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        with Operations.context(MigrationContext.configure(db.connection())):
            import_module(MIGRATION).downgrade()
            assert db.execute(sessions).all() == before_sessions
            assert db.execute(items).all() == before_items
            import_module(MIGRATION).upgrade()
        assert db.execute(sessions).all() == before_sessions
        assert db.execute(items).all() == before_items
        restored = LoadingRepository(db).get(uuid.UUID(loading["id"]))
        assert restored.status == "FINISHED"
        assert restored.organization_id == LEGACY_ORGANIZATION_ID
        assert all(
            item.status == "CHECKED"
            and item.load_plan_id == scenario.load_plan_id
            and item.organization_id == LEGACY_ORGANIZATION_ID
            for item in restored.items
        )


def test_upgrade_rejects_legacy_checklist_from_another_plan_without_losing_rows(
    client,
    session_factory,
):
    first = seed_operational_scenario(session_factory)
    second = seed_operational_scenario(session_factory)
    first_loading = _create_loading(client, first)
    second_loading = _create_loading(client, second)
    identifier = uuid.uuid4()
    with session_factory() as db:
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        with Operations.context(MigrationContext.configure(db.connection())):
            import_module(MIGRATION).downgrade()
        db.execute(
            text(
                "INSERT INTO loading_session_items(id,loading_session_id,load_plan_item_id,status) "
                "VALUES (:id,:session,:item,'PENDING')"
            ),
            {
                "id": identifier,
                "session": uuid.UUID(first_loading["id"]),
                "item": uuid.UUID(second_loading["items"][0]["load_plan_item_id"]),
            },
        )
        before = db.scalar(text("SELECT count(*) FROM loading_session_items"))
        with (
            pytest.raises(DBAPIError, match="G06-B upgrade refused"),
            db.begin_nested(),
            Operations.context(MigrationContext.configure(db.connection())),
        ):
            import_module(MIGRATION).upgrade()
        assert db.scalar(text("SELECT count(*) FROM loading_session_items")) == before
        assert db.scalar(
            text("SELECT loading_session_id FROM loading_session_items WHERE id=:id"),
            {"id": identifier},
        ) == uuid.UUID(first_loading["id"])
        assert "organization_id" not in {
            column["name"]
            for column in inspect(db.connection()).get_columns("loading_sessions")
        }
