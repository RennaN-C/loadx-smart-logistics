import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.schemas import TripCreate
from app.modules.deliveries.service import (
    DeliveryTripNotInRouteError,
    TripAccessForbiddenError,
    TripDeliveriesNotFinishedError,
    TripDriverInactiveError,
    TripLoadingNotFinishedError,
    TripLoadPlanAlreadyAssignedError,
    TripService,
)
from app.modules.drivers.models import Driver
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.status_history.models import StatusHistory
from app.modules.trucks.models import Truck
from app.modules.users.models import User

SQLITE_TABLES = (
    Driver.__table__,
    User.__table__,
    Customer.__table__,
    Truck.__table__,
    Product.__table__,
    Order.__table__,
    OrderItem.__table__,
    StatusHistory.__table__,
    LoadPlan.__table__,
    LoadPlanOrder.__table__,
    LoadPlanItem.__table__,
    Trip.__table__,
    Delivery.__table__,
)


class LoadingState:
    def __init__(self, *, finished: bool) -> None:
        self.finished = finished

    def is_load_plan_finished(self, load_plan_id: uuid.UUID) -> bool:
        del load_plan_id
        return self.finished


def create_user(
    db: Session,
    *,
    role: str,
    driver_id: uuid.UUID | None = None,
) -> User:
    user = User(
        name=f"Usuario {role}",
        email=f"{role.lower()}-{uuid.uuid4()}@example.test",
        password_hash="hash-ficticio",
        role=role,
        driver_id=driver_id,
        active=True,
    )
    db.add(user)
    db.flush()
    return user


def seed_operational_plan(
    db: Session,
    *,
    driver_active: bool = True,
) -> tuple[User, Driver, LoadPlan, list[Order]]:
    driver = Driver(
        name="Motorista Ficticio",
        document=f"DOC-{uuid.uuid4()}",
        phone="5500000000000",
        license_number=f"CNH-{uuid.uuid4()}",
        license_category="D",
        active=driver_active,
    )
    customer = Customer(
        name="Cliente Ficticio",
        document=f"CNPJ-{uuid.uuid4()}",
        address="Rua Exemplo, 100",
        city="Sao Paulo",
        state="SP",
    )
    truck = Truck(
        plate=f"T{uuid.uuid4().hex[:6]}",
        model="Bau de teste",
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=Decimal("1000.00"),
        active=True,
    )
    product = Product(
        code=f"P-{uuid.uuid4()}",
        name="Caixa de teste",
        width_cm=10,
        height_cm=10,
        length_cm=10,
        weight_kg=Decimal("1.000"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )
    db.add_all((driver, customer, truck, product))
    db.flush()

    manager = create_user(db, role="LOGISTICS_MANAGER")
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
                    delivery_sequence=delivery_sequence,
                )
            ],
        )
        for number, delivery_sequence in ((200, 20), (100, 10))
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
        algorithm_version="test-v1",
        approved_at=datetime.now(UTC),
        orders=[LoadPlanOrder(order_id=order.id) for order in orders],
    )
    db.add(plan)
    db.commit()
    return manager, driver, plan, orders


def create_trip(
    db: Session,
    *,
    loading_finished: bool = False,
) -> tuple[TripService, User, Driver, Trip, list[Order]]:
    manager, driver, plan, orders = seed_operational_plan(db)
    service = TripService(
        db,
        loading_reference_service=LoadingState(finished=loading_finished),
    )
    trip = service.create_trip(
        TripCreate(load_plan_id=plan.id, driver_id=driver.id),
        changed_by=manager.id,
    )
    return service, manager, driver, trip, orders


def test_create_trip_generates_deterministic_deliveries_and_history(
    db_session: Session,
) -> None:
    _service, _manager, _driver, trip, orders = create_trip(db_session)

    assert trip.status == "SCHEDULED"
    assert [delivery.sequence for delivery in trip.deliveries] == [1, 2]
    assert [delivery.order_id for delivery in trip.deliveries] == [
        orders[1].id,
        orders[0].id,
    ]
    history = db_session.scalars(select(StatusHistory)).all()
    assert [(row.entity_type, row.new_status) for row in history].count(
        ("TRIP", "SCHEDULED")
    ) == 1
    assert [(row.entity_type, row.new_status) for row in history].count(
        ("DELIVERY", "PENDING")
    ) == 2


def test_create_trip_rejects_inactive_driver_and_duplicate_plan(
    db_session: Session,
) -> None:
    manager, driver, plan, _orders = seed_operational_plan(
        db_session,
        driver_active=False,
    )
    service = TripService(db_session)
    data = TripCreate(load_plan_id=plan.id, driver_id=driver.id)

    with pytest.raises(TripDriverInactiveError):
        service.create_trip(data, changed_by=manager.id)

    driver.active = True
    db_session.commit()
    service.create_trip(data, changed_by=manager.id)
    with pytest.raises(TripLoadPlanAlreadyAssignedError):
        service.create_trip(data, changed_by=manager.id)


def test_trip_start_requires_finished_loading(db_session: Session) -> None:
    service, manager, _driver, trip, _orders = create_trip(db_session)

    with pytest.raises(TripLoadingNotFinishedError):
        service.change_trip_status(trip.id, "IN_ROUTE", current_user=manager)

    assert db_session.get(Trip, trip.id).status == "SCHEDULED"


def test_delivery_cannot_advance_before_trip_is_in_route(db_session: Session) -> None:
    service, manager, _driver, trip, _orders = create_trip(db_session)

    with pytest.raises(DeliveryTripNotInRouteError):
        service.change_delivery_status(
            trip.deliveries[0].id,
            "IN_DELIVERY",
            current_user=manager,
        )


def test_complete_operational_flow_updates_orders_timestamps_and_history(
    db_session: Session,
) -> None:
    service, manager, _driver, trip, orders = create_trip(
        db_session,
        loading_finished=True,
    )

    trip = service.change_trip_status(trip.id, "IN_ROUTE", current_user=manager)
    assert trip.started_at is not None
    assert {db_session.get(Order, order.id).status for order in orders} == {
        "IN_TRANSIT"
    }

    with pytest.raises(TripDeliveriesNotFinishedError):
        service.change_trip_status(trip.id, "FINISHED", current_user=manager)

    for delivery in trip.deliveries:
        service.change_delivery_status(
            delivery.id,
            "IN_DELIVERY",
            current_user=manager,
        )
        delivered = service.change_delivery_status(
            delivery.id,
            "DELIVERED",
            current_user=manager,
        )
        assert delivered.delivered_at is not None
        assert db_session.get(Order, delivery.order_id).status == "DELIVERED"

    finished = service.change_trip_status(trip.id, "FINISHED", current_user=manager)

    assert finished.finished_at is not None
    assert finished.finished_at >= finished.started_at
    assert len(db_session.scalars(select(StatusHistory)).all()) == 13


def test_linked_active_driver_can_access_only_own_trip(db_session: Session) -> None:
    service, _manager, driver, trip, _orders = create_trip(db_session)
    own_user = create_user(db_session, role="DRIVER", driver_id=driver.id)
    other_driver = Driver(
        name="Outro Motorista",
        document=f"DOC-{uuid.uuid4()}",
        phone="5511111111111",
        license_number=f"CNH-{uuid.uuid4()}",
        active=True,
    )
    db_session.add(other_driver)
    db_session.flush()
    other_user = create_user(db_session, role="DRIVER", driver_id=other_driver.id)
    unlinked_user = create_user(db_session, role="DRIVER")
    db_session.commit()

    assert service.get_trip(trip.id, current_user=own_user).id == trip.id
    for forbidden_user in (other_user, unlinked_user):
        with pytest.raises(TripAccessForbiddenError):
            service.get_trip(trip.id, current_user=forbidden_user)

    driver.active = False
    db_session.commit()
    with pytest.raises(TripAccessForbiddenError):
        service.get_trip(trip.id, current_user=own_user)


def test_history_failure_rolls_back_trip_and_orders(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, manager, _driver, trip, orders = create_trip(
        db_session,
        loading_finished=True,
    )

    def fail_history(*_args, **_kwargs) -> None:
        raise RuntimeError("falha ficticia no historico")

    monkeypatch.setattr(
        service.status_history_service,
        "stage_status_change",
        fail_history,
    )

    with pytest.raises(RuntimeError, match="falha ficticia"):
        service.change_trip_status(trip.id, "IN_ROUTE", current_user=manager)

    db_session.expire_all()
    assert db_session.get(Trip, trip.id).status == "SCHEDULED"
    assert {db_session.get(Order, order.id).status for order in orders} == {"PLANNED"}
