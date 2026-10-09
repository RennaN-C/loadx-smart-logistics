"""OC100 maintenance, odometer and operation boundaries on PostgreSQL."""

import uuid
from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ApiError
from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from app.modules.trucks.maintenance_schemas import MaintenanceCreate
from app.modules.trucks.maintenance_service import MaintenanceService
from app.modules.trucks.models import Truck, TruckMaintenance
from app.modules.trucks.service import TruckService
from tests.integration.test_load_planning_api import (
    create_authenticated_user,
    seed_planning_scenario,
)
from tests.integration.test_trucks_api import make_truck_payload


@pytest.fixture
def manager(session_factory):
    return create_authenticated_user(session_factory, "LOGISTICS_MANAGER")


@pytest.fixture
def truck(client, manager):
    result = client.post(
        "/api/v1/trucks", headers=manager.headers, json=make_truck_payload()
    )
    assert result.status_code == 201
    return result.json()


def payload(**changes):
    result = {
        "kind": "PREVENTIVE",
        "starts_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        "description": "Revisão fictícia",
        "workshop": "Oficina exemplo",
        "cost": 150.25,
    }
    result.update(changes)
    return result


def path(truck):
    return f"/api/v1/trucks/{truck['id']}/maintenances"


def create(client, manager, truck, **changes):
    result = client.post(path(truck), headers=manager.headers, json=payload(**changes))
    assert result.status_code == 201, result.text
    return result.json()


def availability(client, manager, truck):
    records = client.get(
        "/api/v1/trucks/operational-status", headers=manager.headers
    ).json()["items"]
    return next(row for row in records if row["id"] == truck["id"])


@pytest.mark.parametrize("kind", ["PREVENTIVE", "CORRECTIVE"])
def test_create_close_restore_and_keep_history(
    client, session_factory, manager, truck, kind
):
    record = create(client, manager, truck, kind=kind, odometer_km=1000)
    status = availability(client, manager, truck)
    assert status["active"] is True
    assert status["has_maintenance_conflict"] is True
    assert status["available"] is False
    assert status["has_operation_conflict"] is False
    next_at = (datetime.now(UTC) + timedelta(days=90)).isoformat()
    closed = client.post(
        f"{path(truck)}/{record['id']}/close",
        headers=manager.headers,
        json={"odometer_km": 1100, "next_service_at": next_at, "next_service_km": 5000},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["closed_at"] is not None
    assert closed.json()["completion_odometer_km"] == 1100
    assert closed.json()["next_service_km"] == 5000
    assert availability(client, manager, truck)["available"] is True
    updated = client.get(
        f"/api/v1/trucks/{truck['id']}", headers=manager.headers
    ).json()
    assert updated["odometer_km"] == 1100
    assert updated["next_service_km"] == 5000
    rows = client.get(path(truck), headers=manager.headers).json()["items"]
    assert len(rows) == 1
    assert rows[0]["id"] == record["id"]
    assert rows[0]["cost"] == 150.25
    assert (
        client.post(
            f"{path(truck)}/{record['id']}/close", headers=manager.headers, json={}
        ).status_code
        == 409
    )
    with session_factory() as db:
        events = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == uuid.UUID(record["id"]))
            .order_by(AuditEvent.created_at)
        ).all()
        assert [row.event_type for row in events] == [
            "MAINTENANCE_CREATED",
            "MAINTENANCE_CLOSED",
        ]


def test_future_and_period_boundaries(client, session_factory, manager, truck):
    start = datetime.now(UTC) + timedelta(days=1)
    end = start + timedelta(hours=2)
    record = create(
        client, manager, truck, starts_at=start.isoformat(), ends_at=end.isoformat()
    )
    assert availability(client, manager, truck)["available"] is True
    with session_factory() as db:
        service = TruckService(db)
        identifier = uuid.UUID(truck["id"])
        assert not service.has_maintenance_conflict(
            identifier, at=start - timedelta(microseconds=1)
        )
        assert service.has_maintenance_conflict(identifier, at=start)
        assert service.has_maintenance_conflict(
            identifier, at=end - timedelta(microseconds=1)
        )
        assert not service.has_maintenance_conflict(identifier, at=end)
    # Closing a future maintenance cancels its window without deleting history.
    assert (
        client.post(
            f"{path(truck)}/{record['id']}/close", headers=manager.headers, json={}
        ).status_code
        == 200
    )
    with session_factory() as db:
        assert not TruckService(db).has_maintenance_conflict(
            uuid.UUID(truck["id"]), at=start
        )


def test_overlapping_blocks_and_archive_are_independent(client, manager, truck):
    first = create(client, manager, truck)
    second = create(client, manager, truck, kind="CORRECTIVE")
    assert (
        client.post(
            f"{path(truck)}/{first['id']}/close", headers=manager.headers, json={}
        ).status_code
        == 200
    )
    assert availability(client, manager, truck)["available"] is False
    client.patch(
        f"/api/v1/trucks/{truck['id']}", headers=manager.headers, json={"active": False}
    )
    assert (
        client.post(
            f"{path(truck)}/{second['id']}/close", headers=manager.headers, json={}
        ).status_code
        == 200
    )
    status = availability(client, manager, truck)
    assert not status["available"]
    assert not status["has_maintenance_conflict"]
    assert not status["active"]
    assert client.get(path(truck), headers=manager.headers).json()["total"] == 2
    assert (
        client.post(path(truck), headers=manager.headers, json=payload()).status_code
        == 409
    )


@pytest.mark.parametrize("km", [900, -1, True, 1.5, None])
def test_odometer_validation_and_monotonicity(client, manager, truck, km):
    url = f"/api/v1/trucks/{truck['id']}"
    assert (
        client.patch(
            url, headers=manager.headers, json={"odometer_km": 1000}
        ).status_code
        == 200
    )
    result = client.patch(url, headers=manager.headers, json={"odometer_km": km})
    assert result.status_code == (409 if km == 900 else 422)
    assert client.get(url, headers=manager.headers).json()["odometer_km"] == 1000


def test_unknown_odometer_and_unchanged_update(client, manager, truck):
    assert truck["odometer_km"] is None
    assert truck["next_service_km"] is None
    record = create(client, manager, truck, cost=None)
    assert record["odometer_km"] is None
    assert record["cost"] is None
    url = f"/api/v1/trucks/{truck['id']}"
    assert (
        client.patch(url, headers=manager.headers, json={"model": "Atualizado"}).json()[
            "odometer_km"
        ]
        is None
    )


@pytest.mark.parametrize(
    "role,read,write",
    [
        ("ADMIN", 200, 201),
        ("LOGISTICS_MANAGER", 200, 201),
        ("CHECKER", 200, 403),
        ("DRIVER", 403, 403),
    ],
)
def test_maintenance_rbac(client, session_factory, manager, truck, role, read, write):
    actor = create_authenticated_user(session_factory, role)
    result = client.post(path(truck), headers=actor.headers, json=payload())
    assert result.status_code == write
    assert client.get(path(truck), headers=actor.headers).status_code == read
    existing = client.get(path(truck), headers=manager.headers).json()["items"]
    if not existing:
        existing = [create(client, manager, truck)]
    response = client.post(
        f"{path(truck)}/{existing[0]['id']}/close", headers=actor.headers, json={}
    )
    assert response.status_code == (200 if write == 201 else 403)
    assert client.get(path(truck)).status_code == 401


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "OTHER"},
        {"starts_at": "2026-10-10T10:00:00"},
        {"cost": -1},
        {"cost": "100"},
        {"description": ""},
        {"ends_at": "2000-01-01T00:00:00Z"},
        {"odometer_km": -10},
    ],
)
def test_create_validation(client, manager, truck, change):
    assert (
        client.post(
            path(truck), headers=manager.headers, json=payload(**change)
        ).status_code
        == 422
    )


def test_invalid_revision_and_scoped_identity(client, manager, truck):
    record = create(client, manager, truck, odometer_km=500)
    url = f"{path(truck)}/{record['id']}/close"
    for change in (
        {"next_service_at": "2000-01-01T00:00:00Z"},
        {"next_service_km": 500},
        {"odometer_km": 499},
    ):
        assert client.post(url, headers=manager.headers, json=change).status_code in (
            409,
            422,
        )
        assert (
            client.get(path(truck), headers=manager.headers).json()["items"][0][
                "closed_at"
            ]
            is None
        )
    assert (
        client.post(
            f"{path(truck)}/{uuid.uuid4()}/close", headers=manager.headers, json={}
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/trucks/{uuid.uuid4()}/maintenances", headers=manager.headers
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "operation", ["plan", "approval", "loading", "trip", "distribution"]
)
def test_maintenance_blocks_new_operations(client, session_factory, manager, operation):
    scenario = seed_planning_scenario(session_factory)
    truck = {"id": str(scenario.truck_id)}
    plan_payload = {"truck_id": truck["id"], "order_ids": [str(scenario.order_id)]}
    plan = client.post(
        "/api/v1/load-plans", headers=manager.headers, json=plan_payload
    ).json()
    if operation in ("loading", "trip"):
        assert (
            client.post(
                f"/api/v1/load-plans/{plan['id']}/approve",
                headers=manager.headers,
                json={},
            ).status_code
            == 200
        )
    create(client, manager, truck)
    if operation == "plan":
        result = client.post(
            "/api/v1/load-plans", headers=manager.headers, json=plan_payload
        )
    elif operation == "approval":
        result = client.post(
            f"/api/v1/load-plans/{plan['id']}/approve", headers=manager.headers, json={}
        )
    elif operation == "loading":
        result = client.post(
            "/api/v1/loading-sessions",
            headers=manager.headers,
            json={"load_plan_id": plan["id"]},
        )
    elif operation == "trip":
        from tests.integration.test_drivers_api import make_driver_payload

        driver = client.post(
            "/api/v1/drivers", headers=manager.headers, json=make_driver_payload()
        ).json()
        result = client.post(
            "/api/v1/trips",
            headers=manager.headers,
            json={"load_plan_id": plan["id"], "driver_id": driver["id"]},
        )
    else:
        result = client.post(
            "/api/v1/load-distributions/preflight",
            headers=manager.headers,
            json={"order_ids": [str(scenario.order_id)]},
        )
        assert result.status_code == 200, result.text
        assert result.json()["eligible_trucks"] == []
        assert result.json()["ineligible_trucks"][0]["reason"] == "TRUCK_IN_MAINTENANCE"
        return
    assert result.status_code == 409, result.text
    assert result.json()["code"] == "TRUCK_IN_MAINTENANCE"
    assert (
        client.get(
            f"/api/v1/load-plans/{plan['id']}", headers=manager.headers
        ).status_code
        == 200
    )


@pytest.mark.parametrize("future", [False, True])
def test_active_loading_conflicts_with_maintenance(
    client, session_factory, manager, future
):
    scenario = seed_planning_scenario(session_factory)
    plan = client.post(
        "/api/v1/load-plans",
        headers=manager.headers,
        json={
            "truck_id": str(scenario.truck_id),
            "order_ids": [str(scenario.order_id)],
        },
    ).json()
    client.post(
        f"/api/v1/load-plans/{plan['id']}/approve", headers=manager.headers, json={}
    )
    assert (
        client.post(
            "/api/v1/loading-sessions",
            headers=manager.headers,
            json={"load_plan_id": plan["id"]},
        ).status_code
        == 201
    )
    truck = {"id": str(scenario.truck_id)}
    change = (
        {"starts_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()}
        if future
        else {}
    )
    result = client.post(path(truck), headers=manager.headers, json=payload(**change))
    assert result.status_code == 409
    assert result.json()["code"] == "TRUCK_OPERATION_CONFLICT"
    assert client.get(path(truck), headers=manager.headers).json()["total"] == 0


def test_audit_failure_rolls_back_maintenance_and_odometer(
    session_factory, manager, truck, monkeypatch
):
    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    with session_factory() as db:
        monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
        with pytest.raises(RuntimeError, match="audit unavailable"):
            MaintenanceService(db).create(
                uuid.UUID(truck["id"]),
                MaintenanceCreate.model_validate(payload(odometer_km=1000)),
                actor=manager.id,
            )
        assert db.get(Truck, uuid.UUID(truck["id"])).odometer_km is None
        assert (
            db.scalars(
                select(TruckMaintenance).where(
                    TruckMaintenance.truck_id == uuid.UUID(truck["id"])
                )
            ).all()
            == []
        )


def test_constraints_and_safe_downgrade(session_factory, truck):
    with session_factory() as db:
        invalid = TruckMaintenance(
            truck_id=uuid.UUID(truck["id"]),
            kind="OTHER",
            starts_at=datetime.now(UTC),
            description="Inválida",
        )
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        record = db.get(Truck, uuid.UUID(truck["id"]))
        record.odometer_km = 1000
        db.commit()
        migration = import_module("migrations.versions.20261009_0018_truck_maintenance")
        with pytest.raises(RuntimeError, match="OC100 downgrade blocked"):
            migration.ensure_safe_downgrade(db.connection())
        db.rollback()
        assert db.get(Truck, uuid.UUID(truck["id"])).odometer_km == 1000


def test_close_failure_rolls_back_revision_and_odometer(
    client, session_factory, manager, truck, monkeypatch
):
    from app.modules.trucks.maintenance_schemas import MaintenanceClose

    record = create(client, manager, truck, odometer_km=1000)

    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    with session_factory() as db:
        monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
        with pytest.raises(RuntimeError):
            MaintenanceService(db).close(
                uuid.UUID(truck["id"]),
                uuid.UUID(record["id"]),
                MaintenanceClose(odometer_km=1200, next_service_km=5000),
                actor=manager.id,
            )
        persisted = db.get(TruckMaintenance, uuid.UUID(record["id"]))
        current = db.get(Truck, uuid.UUID(truck["id"]))
        assert persisted.closed_at is None
        assert current.odometer_km == 1000
        assert current.next_service_km is None


def test_concurrent_loading_and_maintenance_share_truck_lock(
    postgres_engine, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import sessionmaker

    from app.modules.customers.models import Customer
    from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
    from app.modules.loading.models import LoadingSession
    from app.modules.loading.service import LoadingService
    from app.modules.orders.models import Order, OrderItem
    from app.modules.products.models import Product
    from app.modules.trucks.schemas import TruckCreate
    from tests.integration.test_truck_operation_concurrency import _create_plan

    factory = sessionmaker(postgres_engine, autoflush=False)
    with factory() as db:
        truck = TruckService(db).create_truck(
            TruckCreate.model_validate(make_truck_payload())
        )
        plan, order, product, customer = _create_plan(db, truck=truck)
        identifiers = truck.id, plan.id, order.id, product.id, customer.id
        db.commit()
    truck_id, plan_id, order_id, product_id, customer_id = identifiers
    monkeypatch.setattr(
        TruckService, "stage_maintenance_audit", lambda *args, **kwargs: None
    )
    barrier = Barrier(2)

    def maintain():
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                MaintenanceService(db).create(
                    truck_id,
                    MaintenanceCreate.model_validate(payload(cost=None)),
                    actor=uuid.uuid4(),
                )
                return "maintenance"
            except ApiError as error:
                return error.code

    def load():
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                LoadingService(db).create_session(plan_id)
                return "loading"
            except ApiError as error:
                db.rollback()
                return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(maintain), executor.submit(load)]
            results = {future.result(timeout=15) for future in futures}
        assert results in (
            {"maintenance", "TRUCK_IN_MAINTENANCE"},
            {"loading", "TRUCK_OPERATION_CONFLICT"},
        )
        with factory() as db:
            sessions = db.scalars(
                select(LoadingSession).where(LoadingSession.load_plan_id == plan_id)
            ).all()
            maintenance = db.scalars(
                select(TruckMaintenance).where(TruckMaintenance.truck_id == truck_id)
            ).all()
            assert len(sessions) + len(maintenance) == 1
    finally:
        with factory() as db:
            for model, column, identifier in (
                (LoadingSession, LoadingSession.load_plan_id, plan_id),
                (TruckMaintenance, TruckMaintenance.truck_id, truck_id),
                (LoadPlanItem, LoadPlanItem.load_plan_id, plan_id),
                (LoadPlanOrder, LoadPlanOrder.load_plan_id, plan_id),
                (LoadPlan, LoadPlan.id, plan_id),
                (OrderItem, OrderItem.order_id, order_id),
                (Order, Order.id, order_id),
                (Product, Product.id, product_id),
                (Customer, Customer.id, customer_id),
                (Truck, Truck.id, truck_id),
            ):
                db.execute(delete(model).where(column == identifier))
            db.commit()


def test_scheduled_window_blocks_starting_existing_loading(
    client, session_factory, manager
):
    scenario = seed_planning_scenario(session_factory)
    plan = client.post(
        "/api/v1/load-plans",
        headers=manager.headers,
        json={
            "truck_id": str(scenario.truck_id),
            "order_ids": [str(scenario.order_id)],
        },
    ).json()
    client.post(
        f"/api/v1/load-plans/{plan['id']}/approve", headers=manager.headers, json={}
    )
    truck = {"id": str(scenario.truck_id)}
    maintenance = create(
        client,
        manager,
        truck,
        starts_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
    )
    loading = client.post(
        "/api/v1/loading-sessions",
        headers=manager.headers,
        json={"load_plan_id": plan["id"]},
    )
    assert loading.status_code == 201
    with session_factory() as db:
        record = db.get(TruckMaintenance, uuid.UUID(maintenance["id"]))
        record.starts_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    checker = create_authenticated_user(session_factory, "CHECKER")
    response = client.patch(
        f"/api/v1/loading-sessions/{loading.json()['id']}/status",
        headers=checker.headers,
        json={"status": "IN_PROGRESS"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "TRUCK_IN_MAINTENANCE"
