"""OC105 lifecycle, historical references and operation boundaries on PostgreSQL."""

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate, CustomerUpdate
from app.modules.customers.service import CustomerService
from app.modules.orders.models import Order
from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from tests.integration.test_customers_api import make_customer_payload
from tests.integration.test_drivers_api import make_driver_payload
from tests.integration.test_load_planning_api import (
    create_authenticated_user,
    seed_planning_scenario,
)
from tests.integration.test_products_api import make_product_payload
from tests.integration.test_trucks_api import make_truck_payload

SessionFactory = Callable[[], Session]
REGISTRIES = [
    ("customers", make_customer_payload),
    ("products", make_product_payload),
    ("trucks", make_truck_payload),
    ("drivers", make_driver_payload),
]


@pytest.fixture
def manager(session_factory: SessionFactory):
    return create_authenticated_user(session_factory, "LOGISTICS_MANAGER")


@pytest.mark.parametrize("resource,payload", REGISTRIES)
def test_lifecycle_preserves_identity_and_records_atomic_idempotent_audit(
    client: TestClient, session_factory: SessionFactory, manager, resource, payload
) -> None:
    created = client.post(
        f"/api/v1/{resource}", headers=manager.headers, json=payload()
    )
    assert created.status_code == 201
    record = created.json()
    url = f"/api/v1/{resource}/{record['id']}"
    for _ in range(2):
        archived = client.patch(url, headers=manager.headers, json={"active": False})
        assert archived.status_code == 200
        assert archived.json() == {**record, "active": False}
    assert client.get(url, headers=manager.headers).json()["active"] is False
    reactivated = client.patch(url, headers=manager.headers, json={"active": True})
    assert reactivated.status_code == 200
    assert reactivated.json() == record
    with session_factory() as db:
        entries = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == uuid.UUID(record["id"]))
            .order_by(AuditEvent.created_at)
        ).all()
        assert [e.event_type for e in entries] == [
            "RECORD_ARCHIVED",
            "RECORD_REACTIVATED",
        ]
        assert all(
            e.actor_id == manager.id and e.changed_fields == "active" for e in entries
        )


@pytest.mark.parametrize("reactivate", [False, True])
def test_downgrade_guard_preserves_archiving_and_audit(
    client: TestClient, session_factory: SessionFactory, manager, reactivate
) -> None:
    from importlib import import_module

    from sqlalchemy.exc import DBAPIError

    migration = import_module("migrations.versions.20261008_0016_record_archiving")
    created = client.post(
        "/api/v1/customers", headers=manager.headers, json=make_customer_payload()
    )
    assert created.status_code == 201
    customer_id = uuid.UUID(created.json()["id"])
    path = f"/api/v1/customers/{customer_id}"
    assert (
        client.patch(path, headers=manager.headers, json={"active": False}).status_code
        == 200
    )
    if reactivate:
        assert (
            client.patch(
                path, headers=manager.headers, json={"active": True}
            ).status_code
            == 200
        )

    with session_factory() as db:
        events_before = db.scalars(
            select(AuditEvent).where(AuditEvent.entity_id == customer_id)
        ).all()
        assert len(events_before) == (2 if reactivate else 1)
        with pytest.raises(DBAPIError, match="OC105 downgrade blocked"):
            db.execute(migration.DOWNGRADE_GUARD_SQL)
        db.rollback()
        assert db.get(Customer, customer_id).active is reactivate
        events_after = db.scalars(
            select(AuditEvent).where(AuditEvent.entity_id == customer_id)
        ).all()
        assert [event.event_type for event in events_after] == [
            event.event_type for event in events_before
        ]


@pytest.mark.parametrize("resource,payload", REGISTRIES)
def test_archive_filters_are_applied_before_pagination(
    client: TestClient, manager, resource, payload
) -> None:
    created = client.post(
        f"/api/v1/{resource}", headers=manager.headers, json=payload()
    ).json()
    client.patch(
        f"/api/v1/{resource}/{created['id']}",
        headers=manager.headers,
        json={"active": False},
    )
    base = f"/api/v1/{resource}"
    assert client.get(base, headers=manager.headers).json()["total"] == 0
    for archive_status in ("archived", "all"):
        data = client.get(
            base,
            headers=manager.headers,
            params={"archive_status": archive_status, "page_size": 1},
        ).json()
        assert data["total"] == 1 and data["total_pages"] == 1
        assert data["items"][0]["active"] is False
        empty = client.get(
            base,
            headers=manager.headers,
            params={"archive_status": archive_status, "page": 2, "page_size": 1},
        ).json()
        assert empty["items"] == [] and empty["total"] == 1
    assert (
        client.get(
            base, headers=manager.headers, params={"archive_status": "unknown"}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("resource,payload", REGISTRIES)
def test_archived_identity_cannot_be_reused_and_reactivation_keeps_uniqueness(
    client: TestClient, manager, resource, payload
) -> None:
    created = client.post(
        f"/api/v1/{resource}", headers=manager.headers, json=payload()
    ).json()
    url = f"/api/v1/{resource}/{created['id']}"
    client.patch(url, headers=manager.headers, json={"active": False})
    assert (
        client.post(
            f"/api/v1/{resource}", headers=manager.headers, json=payload()
        ).status_code
        == 409
    )
    assert (
        client.patch(url, headers=manager.headers, json={"active": True}).status_code
        == 200
    )
    assert (
        client.patch(url, headers=manager.headers, json={"active": None}).status_code
        == 422
    )


@pytest.mark.parametrize("role", ["ADMIN", "CHECKER", "DRIVER"])
@pytest.mark.parametrize("resource,payload", REGISTRIES)
def test_only_manager_can_change_registry_lifecycle(
    client: TestClient,
    session_factory: SessionFactory,
    manager,
    role,
    resource,
    payload,
) -> None:
    created = client.post(
        f"/api/v1/{resource}", headers=manager.headers, json=payload()
    ).json()
    actor = create_authenticated_user(session_factory, role)
    for active in (False, True):
        result = client.patch(
            f"/api/v1/{resource}/{created['id']}",
            headers=actor.headers,
            json={"active": active},
        )
        assert result.status_code == 403
    assert (
        client.patch(
            f"/api/v1/{resource}/{created['id']}", json={"active": False}
        ).status_code
        == 401
    )


@pytest.mark.parametrize("resource", ["customers", "products"])
def test_archived_order_sources_reject_new_orders_and_planning_but_preserve_history(
    client: TestClient, session_factory: SessionFactory, manager, resource
) -> None:
    scenario = seed_planning_scenario(session_factory)
    with session_factory() as db:
        customer_id = db.get(Order, scenario.order_id).customer_id
    identifier = customer_id if resource == "customers" else scenario.product_id
    plan = client.post(
        "/api/v1/load-plans",
        headers=manager.headers,
        json={
            "truck_id": str(scenario.truck_id),
            "order_ids": [str(scenario.order_id)],
        },
    )
    assert plan.status_code == 201
    original = plan.json()
    assert (
        client.patch(
            f"/api/v1/{resource}/{identifier}",
            headers=manager.headers,
            json={"active": False},
        ).status_code
        == 200
    )
    order_payload = {
        "customer_id": str(customer_id),
        "priority": "NORMAL",
        "delivery_address": "Rua ficticia, 100",
        "items": [
            {
                "product_id": str(scenario.product_id),
                "quantity": 1,
                "delivery_sequence": 1,
            }
        ],
    }
    result = client.post("/api/v1/orders", headers=manager.headers, json=order_payload)
    assert result.status_code == 409 and result.json()["code"] == "RECORD_ARCHIVED"
    for endpoint, body in [
        (
            "/load-plans",
            {"truck_id": str(scenario.truck_id), "order_ids": [str(scenario.order_id)]},
        ),
        (f"/load-plans/{original['id']}/approve", {}),
    ]:
        assert (
            client.post(
                f"/api/v1{endpoint}", headers=manager.headers, json=body
            ).status_code
            == 409
        )
    assert (
        client.get(
            f"/api/v1/load-plans/{original['id']}", headers=manager.headers
        ).json()
        == original
    )
    assert client.get(
        f"/api/v1/orders/{scenario.order_id}", headers=manager.headers
    ).json()["customer_id"] == str(customer_id)
    assert (
        client.get(
            f"/api/v1/{resource}/{identifier}", headers=manager.headers
        ).status_code
        == 200
    )


def test_audit_failure_rolls_back_archive(
    session_factory: SessionFactory, manager, monkeypatch
) -> None:
    with session_factory() as db:
        customer = CustomerService(db).create_customer(
            CustomerCreate.model_validate(make_customer_payload())
        )
        identifier = customer.id

        def fail(*args, **kwargs):
            raise RuntimeError("audit unavailable")

        monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
        with pytest.raises(RuntimeError):
            CustomerService(db).update_customer(
                identifier, CustomerUpdate(active=False), changed_by=manager.id
            )
        assert db.get(Customer, identifier).active is True
        assert (
            db.scalars(
                select(AuditEvent).where(AuditEvent.entity_id == identifier)
            ).all()
            == []
        )


def test_reactivation_validates_legacy_data_and_rolls_back(
    session_factory: SessionFactory, manager
) -> None:
    with session_factory() as db:
        record = Customer(
            name="Legado ficticio",
            document="invalid",
            address="Rua exemplo",
            city="Cidade",
            state="SP",
            active=False,
        )
        db.add(record)
        db.commit()
        with pytest.raises(ApiError) as failure:
            CustomerService(db).update_customer(
                record.id, CustomerUpdate(active=True), changed_by=manager.id
            )
        assert failure.value.status_code == 422
        assert db.get(Customer, record.id).active is False


@pytest.mark.parametrize("operation", ["planning", "loading", "trip"])
def test_archived_truck_cannot_enter_new_operations(
    client: TestClient, session_factory: SessionFactory, manager, operation
) -> None:
    scenario = seed_planning_scenario(session_factory)
    plan = client.post(
        "/api/v1/load-plans",
        headers=manager.headers,
        json={
            "truck_id": str(scenario.truck_id),
            "order_ids": [str(scenario.order_id)],
        },
    ).json()
    assert (
        client.post(
            f"/api/v1/load-plans/{plan['id']}/approve", headers=manager.headers, json={}
        ).status_code
        == 200
    )
    driver = client.post(
        "/api/v1/drivers", headers=manager.headers, json=make_driver_payload()
    ).json()
    assert (
        client.patch(
            f"/api/v1/trucks/{scenario.truck_id}",
            headers=manager.headers,
            json={"active": False},
        ).status_code
        == 200
    )
    if operation == "planning":
        result = client.post(
            f"/api/v1/load-plans/{plan['id']}/recalculate",
            headers=manager.headers,
            json={},
        )
    elif operation == "loading":
        result = client.post(
            "/api/v1/loading-sessions",
            headers=manager.headers,
            json={"load_plan_id": plan["id"]},
        )
    else:
        result = client.post(
            "/api/v1/trips",
            headers=manager.headers,
            json={"load_plan_id": plan["id"], "driver_id": driver["id"]},
        )
    assert result.status_code == 409
    assert (
        client.get(f"/api/v1/load-plans/{plan['id']}", headers=manager.headers).json()[
            "status"
        ]
        == "APPROVED"
    )


def test_archived_driver_cannot_be_assigned_but_existing_trip_remains_visible(
    client: TestClient, session_factory: SessionFactory, manager
) -> None:
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
    driver = client.post(
        "/api/v1/drivers", headers=manager.headers, json=make_driver_payload()
    ).json()
    client.patch(
        f"/api/v1/drivers/{driver['id']}",
        headers=manager.headers,
        json={"active": False},
    )
    payload = {"load_plan_id": plan["id"], "driver_id": driver["id"]}
    result = client.post("/api/v1/trips", headers=manager.headers, json=payload)
    assert result.status_code == 409
    client.patch(
        f"/api/v1/drivers/{driver['id']}",
        headers=manager.headers,
        json={"active": True},
    )
    trip = client.post("/api/v1/trips", headers=manager.headers, json=payload)
    assert trip.status_code == 201
    client.patch(
        f"/api/v1/drivers/{driver['id']}",
        headers=manager.headers,
        json={"active": False},
    )
    historical = client.get(
        f"/api/v1/trips/{trip.json()['id']}", headers=manager.headers
    )
    assert (
        historical.status_code == 200 and historical.json()["driver_id"] == driver["id"]
    )


@pytest.mark.parametrize(
    "resource,payload,replacement,identity",
    [
        (
            "customers",
            make_customer_payload,
            lambda: make_customer_payload("00000000000272"),
            "document",
        ),
        (
            "products",
            make_product_payload,
            lambda: make_product_payload("CX-B"),
            "code",
        ),
        ("trucks", make_truck_payload, lambda: make_truck_payload("DEF2E34"), "plate"),
        (
            "drivers",
            make_driver_payload,
            lambda: make_driver_payload("98765432100", "98765432109"),
            "license_number",
        ),
    ],
)
def test_reactivation_with_duplicate_identity_is_atomic(
    client: TestClient, manager, resource, payload, replacement, identity
) -> None:
    first = client.post(
        f"/api/v1/{resource}", headers=manager.headers, json=payload()
    ).json()
    second = client.post(
        f"/api/v1/{resource}", headers=manager.headers, json=replacement()
    ).json()
    url = f"/api/v1/{resource}/{first['id']}"
    client.patch(url, headers=manager.headers, json={"active": False})
    result = client.patch(
        url, headers=manager.headers, json={"active": True, identity: second[identity]}
    )
    assert result.status_code == 409
    preserved = client.get(url, headers=manager.headers).json()
    assert preserved["active"] is False and preserved[identity] == first[identity]


@pytest.mark.parametrize("resource", ["customers", "products", "trucks", "drivers"])
def test_openapi_documents_lifecycle_and_archive_filter(
    client: TestClient, resource
) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"][f"/api/v1/{resource}"]["get"]
    archive_filter = next(
        p for p in operation["parameters"] if p["name"] == "archive_status"
    )
    assert archive_filter["schema"]["enum"] == ["active", "archived", "all"]
    assert archive_filter["schema"]["default"] == "active"
    name = {
        "customers": "Customer",
        "products": "Product",
        "trucks": "Truck",
        "drivers": "Driver",
    }[resource]
    assert (
        schema["components"]["schemas"][f"{name}Read"]["properties"]["active"]["type"]
        == "boolean"
    )
    assert "active" in schema["components"]["schemas"][f"{name}Update"]["properties"]


@pytest.mark.parametrize("resource", ["customers", "products"])
def test_postgresql_lifecycle_flag_is_nonnull_with_true_default(
    session_factory: SessionFactory, resource
) -> None:
    from sqlalchemy import text

    with session_factory() as db:
        column = db.execute(
            text(
                "SELECT is_nullable, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name=:table AND column_name='active'"
            ),
            {"table": resource},
        ).one()
        assert column.is_nullable == "NO" and column.column_default == "true"


def test_loading_reloads_archive_committed_by_another_process(postgres_engine) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from decimal import Decimal

    from sqlalchemy import delete
    from sqlalchemy.orm import sessionmaker

    from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
    from app.modules.loading.models import LoadingSession
    from app.modules.loading.service import LoadingService
    from app.modules.orders.models import OrderItem
    from app.modules.products.models import Product
    from app.modules.trucks.models import Truck
    from app.modules.trucks.schemas import TruckUpdate
    from app.modules.trucks.service import TruckService
    from tests.integration.test_truck_operation_concurrency import _create_plan

    factory = sessionmaker(postgres_engine, autoflush=False)
    with factory() as db:
        truck = Truck(
            plate=f"A{uuid.uuid4().hex[:6]}",
            model="Arquivo concorrente",
            internal_width_cm=100,
            internal_height_cm=100,
            internal_length_cm=100,
            max_weight_kg=Decimal(1000),
        )
        db.add(truck)
        db.flush()
        plan, order, product, customer = _create_plan(db, truck=truck)
        identifiers = truck.id, plan.id, order.id, product.id, customer.id
        db.commit()
    truck_id, plan_id, order_id, product_id, customer_id = identifiers
    try:
        with factory() as stale_session:
            cached = stale_session.get(Truck, truck_id)
            assert cached.active is True

            def archive():
                with factory() as writer:
                    TruckService(writer).update_truck(
                        truck_id, TruckUpdate(active=False)
                    )

            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(archive).result(timeout=10)
            with pytest.raises(ApiError) as error:
                LoadingService(stale_session).create_session(plan_id)
            assert error.value.code == "RECORD_ARCHIVED"
            assert (
                stale_session.scalars(
                    select(LoadingSession).where(LoadingSession.load_plan_id == plan_id)
                ).all()
                == []
            )
    finally:
        with factory() as db:
            for model, column, identifier in [
                (LoadPlanItem, LoadPlanItem.load_plan_id, plan_id),
                (LoadPlanOrder, LoadPlanOrder.load_plan_id, plan_id),
                (LoadPlan, LoadPlan.id, plan_id),
                (OrderItem, OrderItem.order_id, order_id),
                (Order, Order.id, order_id),
                (Product, Product.id, product_id),
                (Customer, Customer.id, customer_id),
                (Truck, Truck.id, truck_id),
            ]:
                db.execute(delete(model).where(column == identifier))
            db.commit()
