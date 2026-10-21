"""PostgreSQL guards preserve the physical snapshot from first operational use."""

import uuid
from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, insert, text, update
from sqlalchemy.exc import IntegrityError

from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.loading.service import LoadingService
from app.modules.orders.models import Order
from tests.integration.oc90_helpers import seed_multi_flow
from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario

CONSTRAINT = "ck_load_plans__operational_snapshot"


@pytest.fixture(params=["multi_loading", "legacy_loading", "legacy_trip"])
def operated(request, client, session_factory):
    if request.param == "multi_loading":
        s = seed_multi_flow(client, session_factory)
        s.approve()
        s.create_loading(0)
        identifier = uuid.UUID(s.parts[0]["load_plan"]["id"])
    else:
        scenario = seed_operational_scenario(session_factory)
        identifier = scenario.load_plan_id
        if request.param == "legacy_trip":
            # Trip alone is defensive evidence even without any loading.
            create_trip(client, scenario)
        else:
            with session_factory() as db:
                LoadingService(db).create_session(identifier)
    return session_factory, identifier


@pytest.mark.parametrize(
    "mutation",
    [
        "truck",
        "truck_snapshot",
        "metrics",
        "algorithm",
        "delete_plan",
        "plan_identity",
        "position",
        "sequence",
        "product_snapshot",
        "rotation",
        "dimensions",
        "insert_item",
        "delete_item",
        "reassign_item",
        "insert_order",
        "delete_order",
        "reassign_order",
    ],
)
def test_direct_snapshot_mutation_is_rejected_by_stable_guard(operated, mutation):
    factory, identifier = operated
    with factory() as db:
        plan = db.get(LoadPlan, identifier)
        item = plan.items[0]
        # Another real, unused plan/order/truck makes replacement FK targets
        # valid. Local dimensions, sequence, rotation and metrics stay valid.
        spare = seed_operational_scenario(factory)
        spare_plan = db.get(LoadPlan, spare.load_plan_id)
        if mutation == "truck":
            statement = (
                update(LoadPlan)
                .where(LoadPlan.id == identifier)
                .values(truck_id=spare_plan.truck_id)
            )
        elif mutation == "truck_snapshot":
            statement = (
                update(LoadPlan)
                .where(LoadPlan.id == identifier)
                .values(truck_snapshot_model="Outro baú fictício")
            )
        elif mutation == "metrics":
            statement = (
                update(LoadPlan)
                .where(LoadPlan.id == identifier)
                .values(occupancy_percent=50)
            )
        elif mutation == "algorithm":
            statement = (
                update(LoadPlan)
                .where(LoadPlan.id == identifier)
                .values(algorithm_version="outra-versao")
            )
        elif mutation == "delete_plan":
            statement = delete(LoadPlan).where(LoadPlan.id == identifier)
        elif mutation == "plan_identity":
            statement = (
                update(LoadPlan)
                .where(LoadPlan.id == identifier)
                .values(id=uuid.uuid4())
            )
        elif mutation in {
            "position",
            "sequence",
            "product_snapshot",
            "rotation",
            "dimensions",
            "reassign_item",
        }:
            values = {
                "position": {"position_x_cm": item.position_x_cm + 1},
                "sequence": {"loading_sequence": 99},
                "product_snapshot": {"product_snapshot_name": "Outro produto fictício"},
                "rotation": {
                    "rotation_code": "ZYX",
                    "product_snapshot_rotation_allowed": True,
                },
                # Change the dimension and its corresponding snapshot together.
                "dimensions": {"used_width_cm": 11, "product_snapshot_width_cm": 11},
                "reassign_item": {"load_plan_id": spare_plan.id},
            }[mutation]
            statement = (
                update(LoadPlanItem).where(LoadPlanItem.id == item.id).values(**values)
            )
        elif mutation == "insert_item":
            values = {
                column.name: getattr(item, column.name)
                for column in LoadPlanItem.__table__.columns
            }
            values.update(
                id=uuid.uuid4(),
                volume_index=2,
                order_item_snapshot_quantity=2,
                loading_sequence=99,
            )
            # Multi parts may already contain index 2; choose the other index.
            if item.volume_index == 2:
                values["volume_index"] = 1
            statement = insert(LoadPlanItem).values(**values)
        elif mutation == "delete_item":
            statement = delete(LoadPlanItem).where(LoadPlanItem.id == item.id)
        elif mutation == "insert_order":
            statement = insert(LoadPlanOrder).values(
                load_plan_id=identifier, order_id=spare.order_ids[0]
            )
        elif mutation == "reassign_order":
            statement = (
                update(LoadPlanOrder)
                .where(LoadPlanOrder.load_plan_id == identifier)
                .values(load_plan_id=spare_plan.id)
            )
        else:
            statement = delete(LoadPlanOrder).where(
                LoadPlanOrder.load_plan_id == identifier
            )

        def attempt_snapshot_write():
            db.execute(statement)
            db.flush()

        with pytest.raises(IntegrityError) as error:
            attempt_snapshot_write()
        assert error.value.orig.diag.constraint_name == CONSTRAINT
        db.rollback()


def test_noop_updates_remain_allowed_for_all_snapshot_rows(operated):
    factory, identifier = operated
    with factory() as db:
        for table, column in (
            (LoadPlan, "truck_snapshot_model"),
            (LoadPlanItem, "product_snapshot_name"),
            (LoadPlanOrder, "order_id"),
        ):
            predicate = (
                table.id == identifier
                if table is LoadPlan
                else table.load_plan_id == identifier
            )
            attribute = getattr(table, column)
            assert (
                db.execute(
                    update(table).where(predicate).values({column: attribute})
                ).rowcount
                > 0
            )
        db.commit()


def test_reassignment_cannot_insert_an_unoperated_child_into_operated_parent(operated):
    factory, identifier = operated
    spare = seed_operational_scenario(factory)
    with factory() as db:
        # The new parent is operated; the old parent has no operation.

        def attempt_child_reassignment():
            db.execute(
                update(LoadPlanItem)
                .where(LoadPlanItem.load_plan_id == spare.load_plan_id)
                .values(load_plan_id=identifier)
            )

        with pytest.raises(IntegrityError) as error:
            attempt_child_reassignment()
        assert error.value.orig.diag.constraint_name == CONSTRAINT
        db.rollback()


def test_preoperation_create_reprocess_approve_and_snapshot_write_still_work(
    client, session_factory
):
    s = seed_multi_flow(client, session_factory)
    old = s.parts[0]
    prefix = f"/load-distributions/{s.distribution['id']}/parts/{old['id']}"
    s.request("POST", prefix + "/cancel", {})
    s.request(
        "POST",
        prefix + "/reprocess",
        {
            "truck_id": old["load_plan"]["truck_id"],
            "expected_load_plan_id": old["load_plan"]["id"],
        },
    )
    s.approve()
    identifier = uuid.UUID(s.parts[0]["load_plan"]["id"])
    with session_factory() as db:
        db.execute(
            update(LoadPlan)
            .where(LoadPlan.id == identifier)
            .values(truck_snapshot_model="Snapshot pré-operação fictício")
        )
        db.commit()
    loading = s.create_loading(0)
    assert loading["load_plan_id"] == str(identifier)
    with session_factory() as db:
        assert (
            db.get(LoadPlan, identifier).truck_snapshot_model
            == "Snapshot pré-operação fictício"
        )
        assert db.get(Order, uuid.UUID(s.order["id"])).status == "PLANNED"


def test_allowed_downgrade_removes_snapshot_triggers_and_upgrade_restores_them(
    client, session_factory
):
    scenario = seed_operational_scenario(session_factory)
    with session_factory() as db:
        LoadingService(db).create_session(scenario.load_plan_id)
        migration = import_module(
            "migrations.versions.20261020_0028_delivery_distribution_parts"
        )
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        oc94 = import_module("migrations.versions.20261021_0032_trip_cancellation")
        oc94_pause = import_module("migrations.versions.20261021_0033_trip_interruption")
        with Operations.context(MigrationContext.configure(db.connection())):
            oc94_pause.downgrade()
            oc94.downgrade()
            migration.downgrade()
            assert (
                db.scalar(
                    text("SELECT to_regprocedure('protect_operated_load_plan()')")
                )
                is None
            )
            assert (
                db.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'protect_operated_%' AND NOT tgisinternal"
                    )
                )
                == 0
            )
            db.execute(
                update(LoadPlan)
                .where(LoadPlan.id == scenario.load_plan_id)
                .values(truck_snapshot_model="Revisão anterior")
            )
            migration.upgrade()
            oc94.upgrade()
            oc94_pause.upgrade()
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'protect_operated_%' AND NOT tgisinternal"
                )
            )
            == 3
        )

        def attempt_protected_plan_write():
            db.execute(
                update(LoadPlan)
                .where(LoadPlan.id == scenario.load_plan_id)
                .values(truck_snapshot_model="Alteração bloqueada")
            )

        with pytest.raises(IntegrityError) as error:
            attempt_protected_plan_write()
        assert error.value.orig.diag.constraint_name == CONSTRAINT
        db.rollback()
