import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import sessionmaker

from app.modules.customers.models import Customer
from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.schemas import TripCreate
from app.modules.deliveries.service import TripService
from app.modules.drivers.models import Driver
from app.modules.drivers.service import DriverOperationConflictError
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.status_history.models import StatusHistory
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from tests.integration.test_truck_operation_concurrency import _create_plan


def test_concurrent_driver_allocation_on_different_trucks_creates_only_one_trip(
    postgres_engine: Engine,
) -> None:
    session_factory = sessionmaker(bind=postgres_engine, autoflush=False)
    with session_factory() as db:
        driver = Driver(
            name="Motorista concorrencia",
            document=uuid.uuid4().hex,
            phone="41999999999",
            license_number=uuid.uuid4().hex,
            active=True,
        )
        manager = User(
            name="Gestor concorrencia",
            email=f"{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="LOGISTICS_MANAGER",
            active=True,
        )
        trucks = [
            Truck(
                plate=f"C{uuid.uuid4().hex[:6]}",
                model="Caminhao concorrencia",
                internal_width_cm=100,
                internal_height_cm=100,
                internal_length_cm=100,
                max_weight_kg=Decimal("1000.00"),
                active=True,
            )
            for _ in range(2)
        ]
        db.add_all([driver, manager, *trucks])
        db.flush()
        operations = [_create_plan(db, truck=truck) for truck in trucks]
        plan_ids, order_ids, product_ids, customer_ids = (
            tuple(operation[index].id for operation in operations) for index in range(4)
        )
        truck_ids = tuple(truck.id for truck in trucks)
        driver_id, manager_id = driver.id, manager.id
        db.commit()

    barrier = Barrier(2)

    def reserve(plan_id: uuid.UUID) -> str:
        with session_factory() as db:
            barrier.wait(timeout=5)
            try:
                TripService(db).create_trip(
                    TripCreate(load_plan_id=plan_id, driver_id=driver_id),
                    changed_by=manager_id,
                )
            except DriverOperationConflictError:
                return "CONFLICT"
            return "CREATED"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(reserve, plan_id) for plan_id in plan_ids]
            results = [future.result(timeout=15) for future in futures]
        assert sorted(results) == ["CONFLICT", "CREATED"]
        with session_factory() as db:
            trips = db.scalars(select(Trip).where(Trip.driver_id == driver_id)).all()
            assert len(trips) == 1
            assert trips[0].status == "SCHEDULED"
            deliveries = db.scalars(
                select(Delivery).where(Delivery.order_id.in_(order_ids))
            ).all()
            assert len(deliveries) == 1
            assert deliveries[0].trip_id == trips[0].id
            history = db.scalars(
                select(StatusHistory).where(StatusHistory.changed_by == manager_id)
            ).all()
            assert len(history) == 2
    finally:
        with session_factory() as db:
            db.execute(
                delete(StatusHistory).where(StatusHistory.changed_by == manager_id)
            )
            db.execute(delete(Delivery).where(Delivery.order_id.in_(order_ids)))
            db.execute(delete(Trip).where(Trip.driver_id == driver_id))
            db.execute(
                delete(LoadPlanItem).where(LoadPlanItem.load_plan_id.in_(plan_ids))
            )
            db.execute(
                delete(LoadPlanOrder).where(LoadPlanOrder.load_plan_id.in_(plan_ids))
            )
            db.execute(delete(LoadPlan).where(LoadPlan.id.in_(plan_ids)))
            db.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
            db.execute(delete(Order).where(Order.id.in_(order_ids)))
            db.execute(delete(Product).where(Product.id.in_(product_ids)))
            db.execute(delete(Customer).where(Customer.id.in_(customer_ids)))
            db.execute(delete(Truck).where(Truck.id.in_(truck_ids)))
            db.execute(delete(User).where(User.id == manager_id))
            db.execute(delete(Driver).where(Driver.id == driver_id))
            db.commit()
