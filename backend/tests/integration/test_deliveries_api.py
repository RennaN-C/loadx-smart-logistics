import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from app.modules.deliveries.models import Delivery, Trip
from app.modules.drivers.models import Driver
from app.modules.load_planning.models import LoadPlan, LoadPlanOrder
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.status_history.models import StatusHistory
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers

SessionFactory = Callable[[], Session]


@dataclass(frozen=True)
class OperationalScenario:
    load_plan_id: uuid.UUID
    driver_id: uuid.UUID
    order_ids: tuple[uuid.UUID, ...]
    manager_headers: dict[str, str]
    admin_headers: dict[str, str]
    driver_headers: dict[str, str]
    other_driver_headers: dict[str, str]
    checker_headers: dict[str, str]


def seed_operational_scenario(
    session_factory: SessionFactory,
) -> OperationalScenario:
    driver = Driver(
        name="Motorista da Viagem",
        document=f"DOC-{uuid.uuid4().hex[:28]}",
        phone="5500000000000",
        license_number=f"CNH-{uuid.uuid4().hex[:28]}",
        license_category="D",
        active=True,
    )
    other_driver = Driver(
        name="Outro Motorista",
        document=f"DOC-{uuid.uuid4().hex[:28]}",
        phone="5511111111111",
        license_number=f"CNH-{uuid.uuid4().hex[:28]}",
        license_category="D",
        active=True,
    )
    customer = Customer(
        name="Cliente Operacional",
        document=uuid.uuid4().hex,
        address="Rua Exemplo, 100",
        city="Sao Paulo",
        state="SP",
    )
    truck = Truck(
        plate=f"T{uuid.uuid4().hex[:6]}",
        model="Bau operacional",
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=Decimal("1000.00"),
        active=True,
    )
    product = Product(
        code=f"P-{uuid.uuid4().hex}",
        name="Caixa operacional",
        width_cm=10,
        height_cm=10,
        length_cm=10,
        weight_kg=Decimal("1.000"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )

    with session_factory() as db:
        db.add_all((driver, other_driver, customer, truck, product))
        db.flush()
        manager = User(
            name="Gestor Operacional",
            email=f"manager-{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="LOGISTICS_MANAGER",
            active=True,
        )
        admin = User(
            name="Administrador",
            email=f"admin-{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="ADMIN",
            active=True,
        )
        driver_user = User(
            name="Usuario Motorista",
            email=f"driver-{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="DRIVER",
            driver_id=driver.id,
            active=True,
        )
        other_driver_user = User(
            name="Outro Usuario Motorista",
            email=f"driver-{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="DRIVER",
            driver_id=other_driver.id,
            active=True,
        )
        checker = User(
            name="Conferente",
            email=f"checker-{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="CHECKER",
            active=True,
        )
        db.add_all((manager, admin, driver_user, other_driver_user, checker))
        db.flush()

        orders = [
            Order(
                customer_id=customer.id,
                status="PLANNED",
                priority="NORMAL",
                delivery_address=f"Rua Exemplo, {number}",
                items=[
                    OrderItem(
                        product_id=product.id,
                        quantity=1,
                        delivery_sequence=sequence,
                    )
                ],
            )
            for number, sequence in ((200, 20), (100, 10))
        ]
        db.add_all(orders)
        db.flush()
        plan = LoadPlan(
            truck_id=truck.id,
            status="APPROVED",
            truck_snapshot_plate=truck.plate,
            truck_snapshot_model=truck.model,
            truck_snapshot_internal_width_cm=100,
            truck_snapshot_internal_height_cm=100,
            truck_snapshot_internal_length_cm=100,
            truck_snapshot_max_weight_kg=Decimal("1000.00"),
            internal_volume_cm3=1_000_000,
            used_volume_cm3=2_000,
            occupancy_percent=Decimal("0.20"),
            total_weight_kg=Decimal("2.000"),
            loaded_count=2,
            unloaded_count=0,
            algorithm_version="integration-test-v1",
            approved_at=datetime.now(UTC),
            orders=[LoadPlanOrder(order_id=order.id) for order in orders],
        )
        db.add(plan)
        db.commit()
        identities = {
            "manager": manager.id,
            "admin": admin.id,
            "driver": driver_user.id,
            "other_driver": other_driver_user.id,
            "checker": checker.id,
        }
        plan_id = plan.id
        driver_id = driver.id
        order_ids = tuple(order.id for order in orders)

    return OperationalScenario(
        load_plan_id=plan_id,
        driver_id=driver_id,
        order_ids=order_ids,
        manager_headers=issue_session_headers(session_factory, identities["manager"]),
        admin_headers=issue_session_headers(session_factory, identities["admin"]),
        driver_headers=issue_session_headers(session_factory, identities["driver"]),
        other_driver_headers=issue_session_headers(
            session_factory,
            identities["other_driver"],
        ),
        checker_headers=issue_session_headers(session_factory, identities["checker"]),
    )


def create_trip(client: TestClient, scenario: OperationalScenario) -> dict:
    response = client.post(
        "/api/v1/trips",
        json={
            "load_plan_id": str(scenario.load_plan_id),
            "driver_id": str(scenario.driver_id),
        },
        headers=scenario.manager_headers,
    )
    assert response.status_code == 201
    return response.json()


def test_manager_creates_trip_and_deliveries_in_deterministic_order(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    scenario = seed_operational_scenario(session_factory)

    body = create_trip(client, scenario)

    assert body["status"] == "SCHEDULED"
    assert [delivery["sequence"] for delivery in body["deliveries"]] == [1, 2]
    assert [delivery["order_id"] for delivery in body["deliveries"]] == [
        str(scenario.order_ids[1]),
        str(scenario.order_ids[0]),
    ]
    duplicate = client.post(
        "/api/v1/trips",
        json={
            "load_plan_id": str(scenario.load_plan_id),
            "driver_id": str(scenario.driver_id),
        },
        headers=scenario.manager_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "TRIP_LOAD_PLAN_ALREADY_ASSIGNED"


def test_trip_routes_enforce_role_and_object_level_driver_access(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    trip_path = f"/api/v1/trips/{trip['id']}"

    assert client.get(trip_path, headers=scenario.admin_headers).status_code == 200
    assert client.get(trip_path, headers=scenario.driver_headers).status_code == 200
    forbidden = client.get(trip_path, headers=scenario.other_driver_headers)
    checker = client.get(trip_path, headers=scenario.checker_headers)

    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "AUTH_FORBIDDEN"
    assert checker.status_code == 403
    assert checker.json()["code"] == "AUTH_FORBIDDEN"


def test_trip_start_fails_closed_until_loading_is_finished(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)

    response = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=scenario.manager_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "TRIP_LOADING_NOT_FINISHED"


def test_linked_driver_completes_atomic_trip_delivery_and_order_flow(
    client: TestClient,
    session_factory: SessionFactory,
    monkeypatch,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    monkeypatch.setattr(
        LoadingReferenceService,
        "is_load_plan_finished",
        lambda _self, _load_plan_id: True,
    )

    started = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=scenario.driver_headers,
    )
    assert started.status_code == 200
    assert started.json()["started_at"] is not None

    for delivery in started.json()["deliveries"]:
        in_delivery = client.patch(
            f"/api/v1/deliveries/{delivery['id']}/status",
            json={"status": "IN_DELIVERY"},
            headers=scenario.driver_headers,
        )
        assert in_delivery.status_code == 200
        delivered = client.patch(
            f"/api/v1/deliveries/{delivery['id']}/status",
            json={"status": "DELIVERED"},
            headers=scenario.driver_headers,
        )
        assert delivered.status_code == 200
        assert delivered.json()["delivered_at"] is not None

    finished = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "FINISHED"},
        headers=scenario.driver_headers,
    )
    assert finished.status_code == 200
    assert finished.json()["finished_at"] is not None

    with session_factory() as db:
        assert {db.get(Order, order_id).status for order_id in scenario.order_ids} == {
            "DELIVERED"
        }
        assert len(db.scalars(select(StatusHistory)).all()) == 13
        persisted = db.get(Trip, uuid.UUID(trip["id"]))
        assert persisted is not None
        assert persisted.status == "FINISHED"
        assert all(
            delivery.status == "DELIVERED"
            for delivery in db.scalars(
                select(Delivery).where(Delivery.trip_id == persisted.id)
            )
        )
