import uuid
from importlib import import_module

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError

from app.modules.deliveries.models import Delivery, Trip
from app.modules.load_planning.reference_service import LoadPlanReferenceService
from app.modules.orders.models import Order
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.service import StatusHistoryService
from tests.integration.oc90_helpers import seed_multi_flow


@pytest.fixture
def multi(client, session_factory):
    s = seed_multi_flow(client, session_factory)
    s.approve()
    return s


def test_current_part_and_distribution_both_require_approval(client, session_factory):
    s = seed_multi_flow(client, session_factory)
    for part in s.parts:
        with session_factory() as db:
            ref = LoadPlanReferenceService(db)
            assert not ref.get_operational_plan(
                uuid.UUID(part["load_plan"]["id"])
            ).operational_ready
        assert (
            s.request(
                "POST",
                "/loading-sessions",
                {"load_plan_id": part["load_plan"]["id"]},
                expected=409,
            )["code"]
            == "LOADING_PLAN_NOT_APPROVED"
        )
    part = s.parts[0]
    s.request(
        "POST",
        f"/load-distributions/{s.distribution['id']}/parts/{part['id']}/approve",
        {},
    )
    with session_factory() as db:
        assert (
            not LoadPlanReferenceService(db)
            .get_operational_plan(uuid.UUID(part["load_plan"]["id"]))
            .operational_ready
        )
    s.approve()
    for part in s.parts:
        with session_factory() as db:
            ref = LoadPlanReferenceService(db)
            plan = ref.get_operational_plan(uuid.UUID(part["load_plan"]["id"]))
            assert plan.operational_ready
            assert ref.get_distribution_part_for_plan(plan.id).order_ids == (
                uuid.UUID(s.order["id"]),
            )


def test_old_reprocessed_part_is_never_operational(client, session_factory):
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
    with session_factory() as db:
        assert (
            not LoadPlanReferenceService(db)
            .get_operational_plan(uuid.UUID(old["load_plan"]["id"]))
            .operational_ready
        )
    assert (
        s.request(
            "POST",
            "/trips",
            {"load_plan_id": old["load_plan"]["id"], "driver_id": s.drivers[0]["id"]},
            expected=409,
        )["code"]
        == "TRIP_LOAD_PLAN_NOT_APPROVED"
    )
    assert (
        s.request(
            "POST",
            "/loading-sessions",
            {"load_plan_id": old["load_plan"]["id"]},
            expected=409,
        )["code"]
        == "LOADING_PLAN_NOT_APPROVED"
    )


def test_later_leg_can_be_created_after_first_leg_started(multi):
    s = multi
    s.prepare_loadings()
    s.finish_loading(0)
    s.trips = [s.create_trip(0)]
    s.trip_status(0, "IN_ROUTE")
    # Missing delivery in a required part must also prevent aggregate completion.
    s.complete_delivery(0)
    assert s.status() == "IN_TRANSIT"
    s.trips.append(s.create_trip(1))
    assert s.trips[1]["status"] == "SCHEDULED"


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_part",
        "no_part",
        "unknown_part",
        "wrong_order",
        "reassign_trip",
        "reassign_delivery",
        "rewrite_part",
        "rewrite_distribution",
        "rewrite_volume",
    ],
)
def test_database_rejects_inconsistent_direct_writes(multi, mutation):
    s = multi
    s.trips = [s.create_trip(0)]
    trip = s.trips[0]
    part = s.parts[0]
    with s.factory() as db:

        def attempt_invalid_direct_write():
            if mutation in {"wrong_part", "no_part", "unknown_part", "wrong_order"}:
                db.add(
                    Delivery(
                        trip_id=uuid.UUID(trip["id"]),
                        order_id=uuid.uuid4()
                        if mutation == "wrong_order"
                        else uuid.UUID(s.order["id"]),
                        distribution_part_id={
                            "wrong_part": uuid.UUID(s.parts[1]["id"]),
                            "no_part": None,
                            "unknown_part": uuid.uuid4(),
                            "wrong_order": uuid.UUID(part["id"]),
                        }[mutation],
                        status="PENDING",
                        sequence=2,
                    )
                )
            elif mutation == "reassign_trip":
                db.execute(
                    update(Trip)
                    .where(Trip.id == uuid.UUID(trip["id"]))
                    .values(load_plan_id=uuid.UUID(s.parts[1]["load_plan"]["id"]))
                )
            elif mutation == "reassign_delivery":
                db.execute(
                    update(Delivery)
                    .where(Delivery.trip_id == uuid.UUID(trip["id"]))
                    .values(distribution_part_id=uuid.UUID(s.parts[1]["id"]))
                )
            elif mutation == "rewrite_part":
                db.execute(
                    text(
                        "UPDATE load_distribution_parts SET load_plan_id=:plan WHERE id=:part"
                    ),
                    {
                        "plan": uuid.UUID(s.parts[1]["load_plan"]["id"]),
                        "part": uuid.UUID(part["id"]),
                    },
                )
            elif mutation == "rewrite_distribution":
                db.execute(
                    text(
                        "UPDATE load_distributions SET status='CANCELED' WHERE id=:id"
                    ),
                    {"id": uuid.UUID(s.distribution["id"])},
                )
            else:
                db.execute(
                    text("DELETE FROM load_distribution_volumes WHERE part_id=:part"),
                    {"part": uuid.UUID(part["id"])},
                )
            db.flush()
            db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

        with pytest.raises(IntegrityError):
            attempt_invalid_direct_write()
        db.rollback()
    assert s.request("GET", f"/trips/{trip['id']}") == trip
    assert s.status() == "PLANNED"


def test_duplicate_part_order_is_rejected_and_downgrade_preserves_legs(
    multi, monkeypatch
):
    s = multi
    s.trips = [s.create_trip(i) for i in range(2)]
    with s.factory() as db:
        db.add(
            Delivery(
                trip_id=uuid.UUID(s.trips[0]["id"]),
                order_id=uuid.UUID(s.order["id"]),
                distribution_part_id=uuid.UUID(s.parts[0]["id"]),
                status="PENDING",
                sequence=2,
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
        migration = import_module(
            "migrations.versions.20261020_0028_delivery_distribution_parts"
        )
        monkeypatch.setattr(migration.op, "get_bind", lambda: db.connection())
        with pytest.raises(RuntimeError, match="OC90 downgrade blocked"):
            migration.downgrade()
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'protect_operated_%' AND NOT tgisinternal"
                )
            )
            == 3
        )
        assert (
            len(
                db.scalars(
                    select(Delivery).where(
                        Delivery.order_id == uuid.UUID(s.order["id"])
                    )
                ).all()
            )
            == 2
        )


def test_completion_rollback_preserves_both_legs_and_history(multi, monkeypatch):
    s = multi
    s.prepare_loadings()
    s.trips = [s.create_trip(i) for i in range(2)]
    for i in range(2):
        s.finish_loading(i)
        s.trip_status(i, "IN_ROUTE")
    s.complete_delivery(0)
    second = s.trips[1]["deliveries"][0]["id"]
    s.request("PATCH", f"/deliveries/{second}/status", {"status": "IN_DELIVERY"})
    original = StatusHistoryService.stage_status_change

    def failing(service, data):
        if data.entity_type == "ORDER" and data.new_status == "DELIVERED":
            raise RuntimeError("simulated audit failure")
        return original(service, data)

    with monkeypatch.context() as patch:
        patch.setattr(StatusHistoryService, "stage_status_change", failing)
        s.request("POST", f"/deliveries/{second}/receipt", {}, expected=500)
    assert s.status() == "IN_TRANSIT"
    with s.factory() as db:
        assert db.get(Delivery, uuid.UUID(second)).status == "IN_DELIVERY"
        assert not db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id == uuid.UUID(second),
                StatusHistory.new_status == "DELIVERED",
            )
        ).all()
    s.request("POST", f"/deliveries/{second}/receipt", {})
    assert s.status() == "DELIVERED"


def test_multi_preserves_authorization_and_driver_ownership(multi):
    s = multi
    s.prepare_loadings()
    s.trips = [s.create_trip(i) for i in range(2)]
    trip = s.trips[0]
    # Each driver's access remains confined to their own physical leg.
    s.request("GET", f"/trips/{trip['id']}", headers=s.driver_headers[0])
    s.request("GET", f"/trips/{trip['id']}", expected=403, headers=s.driver_headers[1])
    s.request(
        "PATCH",
        f"/trips/{trip['id']}/status",
        {"status": "IN_ROUTE"},
        expected=403,
        headers=s.checker,
    )
    s.request(
        "POST",
        f"/deliveries/{trip['deliveries'][0]['id']}/receipt",
        {},
        expected=403,
        headers=s.driver_headers[1],
    )
    s.request("GET", f"/trips/{trip['id']}", headers=s.admin)
    assert s.status() == "PLANNED"


def test_order_without_volumes_in_part_is_rejected_by_database(multi):
    s = multi
    other = s.request(
        "POST",
        "/orders",
        {
            "customer_id": s.order["customer_id"],
            "priority": "NORMAL",
            "delivery_address": "Outro destino fictício",
            "items": [
                {
                    "product_id": s.order["items"][0]["product_id"],
                    "quantity": 1,
                    "delivery_sequence": 1,
                }
            ],
        },
        expected=201,
    )
    trip = s.create_trip(0)
    with s.factory() as db:
        db.add(
            Delivery(
                trip_id=uuid.UUID(trip["id"]),
                order_id=uuid.UUID(other["id"]),
                distribution_part_id=uuid.UUID(s.parts[0]["id"]),
                status="PENDING",
                sequence=2,
            )
        )
        with pytest.raises(IntegrityError) as error:
            db.flush()
        assert error.value.orig.diag.constraint_name == "ck_deliveries__part_context"
        db.rollback()


def test_order_completes_only_its_required_subset_of_three_parts(
    client, session_factory
):
    s = seed_multi_flow(client, session_factory, optimize=False)
    other = s.request(
        "POST",
        "/orders",
        {
            "customer_id": s.order["customer_id"],
            "priority": "NORMAL",
            "delivery_address": "Outro destino fictício",
            "items": [
                {
                    "product_id": s.order["items"][0]["product_id"],
                    "quantity": 1,
                    "delivery_sequence": 1,
                }
            ],
        },
        expected=201,
    )
    s.request("PATCH", f"/orders/{other['id']}/status", {"status": "READY"})
    s.drivers.append(
        s.request(
            "POST",
            "/drivers",
            {
                "name": "Terceiro fictício",
                "document": "52998224725",
                "phone": "11900000000",
                "license_number": "22345678990",
                "license_category": "D",
            },
            expected=201,
        )
    )
    s.request(
        "POST",
        "/trucks",
        {
            "plate": uuid.uuid4().hex[:7],
            "model": "Terceiro fictício",
            "internal_width_cm": 10,
            "internal_height_cm": 10,
            "internal_length_cm": 10,
            "max_weight_kg": 10,
        },
        expected=201,
    )
    s.distribution = s.request(
        "POST",
        "/load-distributions/optimize",
        {"order_ids": [s.order["id"], other["id"]]},
        expected=201,
    )
    assert s.distribution["truck_count"] == 3
    s.approve()
    s.loadings = [s.create_loading(i) for i in range(3)]
    s.trips = [None] * 3
    required_indices = [
        i
        for i, p in enumerate(s.parts)
        if any(item["order_id"] == s.order["id"] for item in p["load_plan"]["items"])
    ]
    assert len(required_indices) == 2
    for index in required_indices:
        s.finish_loading(index)
        s.trips[index] = s.create_trip(index)
        s.trip_status(index, "IN_ROUTE")
    first, last = required_indices
    s.complete_delivery(first)
    assert s.status() == "IN_TRANSIT"
    s.trip_status(first, "FINISHED")
    s.complete_delivery(last)
    assert s.status() == "DELIVERED"
    with session_factory() as db:
        assert db.get(Order, uuid.UUID(other["id"])).status == "PLANNED"


def test_legacy_unique_order_survives_across_different_trips(client, session_factory):
    from tests.integration.test_deliveries_api import (
        create_trip,
        seed_operational_scenario,
    )

    first = create_trip(client, seed_operational_scenario(session_factory))
    second = create_trip(client, seed_operational_scenario(session_factory))
    with session_factory() as db:
        db.add(
            Delivery(
                trip_id=uuid.UUID(second["id"]),
                order_id=uuid.UUID(first["deliveries"][0]["order_id"]),
                status="PENDING",
                sequence=3,
            )
        )
        with pytest.raises(IntegrityError) as error:
            db.flush()
        assert error.value.orig.diag.constraint_name == "uq_deliveries__legacy_order"
        db.rollback()


def test_migration_backfills_operated_single_part_and_preserves_legacy(
    client, session_factory
):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from tests.integration.test_deliveries_api import (
        create_trip,
        seed_operational_scenario,
    )

    legacy = create_trip(client, seed_operational_scenario(session_factory))
    s = seed_multi_flow(client, session_factory, optimize=False)
    truck = s.request(
        "POST",
        "/trucks",
        {
            "plate": uuid.uuid4().hex[:7],
            "model": "Baú duplo fictício",
            "internal_width_cm": 20,
            "internal_height_cm": 10,
            "internal_length_cm": 10,
            "max_weight_kg": 10,
        },
        expected=201,
    )
    s.distribution = s.request(
        "POST",
        "/load-distributions",
        {
            "order_ids": [s.order["id"]],
            "parts": [
                {
                    "truck_id": truck["id"],
                    "volumes": [
                        {"order_item_id": s.order["items"][0]["id"], "volume_index": i}
                        for i in (1, 2)
                    ],
                }
            ],
        },
        expected=201,
    )
    s.approve()
    migration = import_module(
        "migrations.versions.20261020_0028_delivery_distribution_parts"
    )
    trip_id, delivery_id = uuid.uuid4(), uuid.uuid4()
    with session_factory() as db:
        before = db.scalars(select(StatusHistory.id)).all()
        # Savepoint-backed fixtures have not committed deferred OC87 events.
        # Flush their validation before schema DDL, as a real migration sees.
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        oc94 = import_module("migrations.versions.20261021_0032_trip_cancellation")
        oc94_pause = import_module(
            "migrations.versions.20261021_0033_trip_interruption"
        )
        with Operations.context(MigrationContext.configure(db.connection())):
            oc94_pause.downgrade()
            oc94.downgrade()
            migration.downgrade()
            db.execute(
                text(
                    "INSERT INTO trips (id,load_plan_id,driver_id) VALUES (:id,:plan,:driver)"
                ),
                {
                    "id": trip_id,
                    "plan": uuid.UUID(s.parts[0]["load_plan"]["id"]),
                    "driver": uuid.UUID(s.drivers[0]["id"]),
                },
            )
            db.execute(
                text(
                    "INSERT INTO deliveries (id,trip_id,order_id,sequence) VALUES (:id,:trip,:order,1)"
                ),
                {"id": delivery_id, "trip": trip_id, "order": uuid.UUID(s.order["id"])},
            )
            migration.upgrade()
            oc94.upgrade()
            oc94_pause.upgrade()
        assert db.get(Delivery, delivery_id).distribution_part_id == uuid.UUID(
            s.parts[0]["id"]
        )
        assert (
            db.get(
                Delivery, uuid.UUID(legacy["deliveries"][0]["id"])
            ).distribution_part_id
            is None
        )
        assert set(db.scalars(select(StatusHistory.id)).all()) == set(before)
        assert (
            db.scalar(text("SELECT version_num FROM alembic_version"))
            == "20261021_0033"
        )


def test_trip_creation_rollback_does_not_leave_half_leg(multi, monkeypatch):
    s = multi
    first = s.create_trip(0)
    original = StatusHistoryService.stage_status_change

    def failing(service, data):
        if data.entity_type == "DELIVERY":
            raise RuntimeError("simulated leg creation audit failure")
        return original(service, data)

    with monkeypatch.context() as patch:
        patch.setattr(StatusHistoryService, "stage_status_change", failing)
        s.request(
            "POST",
            "/trips",
            {
                "load_plan_id": s.parts[1]["load_plan"]["id"],
                "driver_id": s.drivers[1]["id"],
            },
            expected=500,
        )
    with s.factory() as db:
        assert not db.scalars(
            select(Trip).where(
                Trip.load_plan_id == uuid.UUID(s.parts[1]["load_plan"]["id"])
            )
        ).all()
        assert (
            len(
                db.scalars(
                    select(Delivery).where(
                        Delivery.order_id == uuid.UUID(s.order["id"])
                    )
                ).all()
            )
            == 1
        )
    assert s.request("GET", f"/trips/{first['id']}") == first
    assert s.create_trip(1)["status"] == "SCHEDULED"


def test_custom_delivery_permission_operates_leg_without_manager_inheritance(multi):
    from tests.integration.auth_helpers import issue_session_headers
    from tests.integration.test_access_profiles import create_profile, custom_user

    s = multi
    profile = create_profile(s.client, s.admin, permissions=["loadx.deliveries.manage"])
    user = custom_user(s.client, s.admin, profile)
    headers = issue_session_headers(s.factory, uuid.UUID(user["id"]))
    s.prepare_loadings()
    s.finish_loading(0)
    s.trips = [s.create_trip(0)]
    s.trip_status(0, "IN_ROUTE")
    delivery_id = s.trips[0]["deliveries"][0]["id"]
    s.request("PATCH", f"/deliveries/{delivery_id}/status", {"status": "IN_DELIVERY"})
    s.request("GET", f"/trips/{s.trips[0]['id']}", headers=headers, expected=403)
    s.request(
        "PATCH",
        f"/trips/{s.trips[0]['id']}/status",
        {"status": "FINISHED"},
        headers=headers,
        expected=403,
    )
    receipt = s.request(
        "POST", f"/deliveries/{delivery_id}/receipt", {}, headers=headers
    )
    assert s.status() == "IN_TRANSIT"
    assert (
        s.request("POST", f"/deliveries/{delivery_id}/receipt", {}, headers=headers)
        == receipt
    )
    s.request(
        "GET", f"/deliveries/{delivery_id}/receipt", headers=headers, expected=403
    )


def test_database_rejects_valid_part_from_another_distribution(multi):
    s = multi
    other = s.request(
        "POST",
        "/orders",
        {
            "customer_id": s.order["customer_id"],
            "priority": "NORMAL",
            "delivery_address": "Outro destino fictício",
            "items": [
                {
                    "product_id": s.order["items"][0]["product_id"],
                    "quantity": 1,
                    "delivery_sequence": 1,
                }
            ],
        },
        expected=201,
    )
    s.request("PATCH", f"/orders/{other['id']}/status", {"status": "READY"})
    truck = s.request(
        "POST",
        "/trucks",
        {
            "plate": uuid.uuid4().hex[:7],
            "model": "Outro fictício",
            "internal_width_cm": 10,
            "internal_height_cm": 10,
            "internal_length_cm": 10,
            "max_weight_kg": 10,
        },
        expected=201,
    )
    distribution = s.request(
        "POST",
        "/load-distributions",
        {
            "order_ids": [other["id"]],
            "parts": [
                {
                    "truck_id": truck["id"],
                    "volumes": [
                        {"order_item_id": other["items"][0]["id"], "volume_index": 1}
                    ],
                }
            ],
        },
        expected=201,
    )
    s.request("POST", f"/load-distributions/{distribution['id']}/approve", {})
    trip = s.create_trip(0)
    with s.factory() as db:
        db.add(
            Delivery(
                trip_id=uuid.UUID(trip["id"]),
                order_id=uuid.UUID(s.order["id"]),
                distribution_part_id=uuid.UUID(distribution["parts"][0]["id"]),
                status="PENDING",
                sequence=2,
            )
        )
        with pytest.raises(IntegrityError) as error:
            db.flush()
        assert error.value.orig.diag.constraint_name == "ck_deliveries__part_context"
        db.rollback()


def test_database_prevents_legacy_order_or_plan_becoming_multi_after_delivery(multi):
    from tests.integration.test_deliveries_api import (
        create_trip,
        seed_operational_scenario,
    )

    s = multi
    legacy = create_trip(s.client, seed_operational_scenario(s.factory))
    with s.factory() as db:

        def attempt_attach_legacy_order():
            db.execute(
                text(
                    "INSERT INTO load_distribution_orders (distribution_id,order_id,active) VALUES (:distribution,:order,true)"
                ),
                {
                    "distribution": uuid.UUID(s.distribution["id"]),
                    "order": uuid.UUID(legacy["deliveries"][0]["order_id"]),
                },
            )

        with pytest.raises(IntegrityError) as error:
            attempt_attach_legacy_order()
        assert error.value.orig.diag.constraint_name == "ck_deliveries__assignment"
        db.rollback()

        def attempt_attach_legacy_plan():
            db.execute(
                text(
                    "INSERT INTO load_distribution_parts (id,distribution_id,load_plan_id,status) VALUES (:id,:distribution,:plan,'PENDING')"
                ),
                {
                    "id": uuid.uuid4(),
                    "distribution": uuid.UUID(s.distribution["id"]),
                    "plan": uuid.UUID(legacy["load_plan_id"]),
                },
            )

        with pytest.raises(IntegrityError) as error:
            attempt_attach_legacy_plan()
        assert error.value.orig.diag.constraint_name == "ck_deliveries__part_context"
        db.rollback()


def test_loading_start_rechecks_operational_boundary_for_stale_session(
    client, session_factory
):
    from app.modules.loading.models import LoadingSession

    s = seed_multi_flow(client, session_factory)
    # Recheck startup even if a stale session was persisted outside the service.
    with session_factory() as db:
        loading = LoadingSession(
            load_plan_id=uuid.UUID(s.parts[0]["load_plan"]["id"]), status="PENDING"
        )
        db.add(loading)
        db.commit()
        identifier = loading.id
    result = s.request(
        "PATCH",
        f"/loading-sessions/{identifier}/status",
        {"status": "IN_PROGRESS"},
        headers=s.checker,
        expected=409,
    )
    assert result["code"] == "LOADING_PLAN_NOT_APPROVED"
    with session_factory() as db:
        assert db.get(LoadingSession, identifier).status == "PENDING"


def test_upgrade_rejects_inconsistent_old_delivery_without_losing_data(multi):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    s = multi
    other = s.request(
        "POST",
        "/orders",
        {
            "customer_id": s.order["customer_id"],
            "priority": "NORMAL",
            "delivery_address": "Destino fictício",
            "items": [
                {
                    "product_id": s.order["items"][0]["product_id"],
                    "quantity": 1,
                    "delivery_sequence": 1,
                }
            ],
        },
        expected=201,
    )
    migration = import_module(
        "migrations.versions.20261020_0028_delivery_distribution_parts"
    )
    trip_id, delivery_id = uuid.uuid4(), uuid.uuid4()
    with s.factory() as db:
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        oc94 = import_module("migrations.versions.20261021_0032_trip_cancellation")
        oc94_pause = import_module(
            "migrations.versions.20261021_0033_trip_interruption"
        )
        with Operations.context(MigrationContext.configure(db.connection())):
            oc94_pause.downgrade()
            oc94.downgrade()
            migration.downgrade()
        db.execute(
            text(
                "INSERT INTO trips (id,load_plan_id,driver_id) VALUES (:id,:plan,:driver)"
            ),
            {
                "id": trip_id,
                "plan": uuid.UUID(s.parts[0]["load_plan"]["id"]),
                "driver": uuid.UUID(s.drivers[0]["id"]),
            },
        )
        db.execute(
            text(
                "INSERT INTO deliveries (id,trip_id,order_id,sequence) VALUES (:id,:trip,:order,1)"
            ),
            {"id": delivery_id, "trip": trip_id, "order": uuid.UUID(other["id"])},
        )
        with (
            pytest.raises(IntegrityError) as error,
            db.begin_nested(),
            Operations.context(MigrationContext.configure(db.connection())),
        ):
            migration.upgrade()
        assert error.value.orig.diag.constraint_name == "ck_deliveries__part_context"
        assert (
            db.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_name='deliveries' AND column_name='distribution_part_id'"
                )
            )
            == 0
        )
        assert db.scalar(
            text("SELECT order_id FROM deliveries WHERE id=:id"), {"id": delivery_id}
        ) == uuid.UUID(other["id"])
