from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import sessionmaker

from app.modules.customers.models import Customer
from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.service import TripService
from app.modules.drivers.models import Driver
from app.modules.load_planning.models import LoadPlan, LoadPlanOrder
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.status_history.models import StatusHistory
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from tests.unit.test_delivery_service import prepare_receipt_delivery


def test_concurrent_receipts_refresh_locked_state_and_share_one_completion(
    postgres_engine: Engine,
) -> None:
    session_factory = sessionmaker(bind=postgres_engine, autoflush=False)
    with session_factory() as db:
        _service, manager, driver, trip, delivery, orders = prepare_receipt_delivery(db)
        manager_id, driver_id, trip_id, delivery_id = (
            manager.id,
            driver.id,
            trip.id,
            delivery.id,
        )
        plan_id = trip.load_plan_id
        truck_id = db.get(LoadPlan, plan_id).truck_id
        order_ids = tuple(order.id for order in orders)
        customer_id = orders[0].customer_id
        product_id = orders[0].items[0].product_id
        history_count = len(
            db.scalars(
                select(StatusHistory).where(StatusHistory.changed_by == manager_id)
            ).all()
        )

    barrier = Barrier(2)

    def register():
        with session_factory() as db:
            user = db.get(User, manager_id)
            # Keep both identity maps stale before either obtains the write lock.
            snapshot = db.get(Delivery, delivery_id)
            trip_snapshot = db.get(Trip, trip_id)
            assert snapshot.status == "IN_DELIVERY"
            assert trip_snapshot.status == "IN_ROUTE"
            barrier.wait(timeout=5)
            return TripService(db).register_delivery_receipt(
                delivery_id, current_user=user
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(register) for _ in range(2)]
            receipts = [future.result(timeout=15) for future in futures]
        assert receipts[0] == receipts[1]
        with session_factory() as db:
            history = db.scalars(
                select(StatusHistory).where(StatusHistory.changed_by == manager_id)
            ).all()
            assert len(history) == history_count + 2
            completions = [
                row
                for row in history
                if row.entity_type == "DELIVERY"
                and row.entity_id == delivery_id
                and row.new_status == "DELIVERED"
            ]
            assert len(completions) == 1
            assert receipts[0].id == completions[0].id
            assert db.get(Delivery, delivery_id).status == "DELIVERED"
    finally:
        with session_factory() as db:
            db.execute(
                delete(StatusHistory).where(StatusHistory.changed_by == manager_id)
            )
            db.execute(delete(Delivery).where(Delivery.trip_id == trip_id))
            db.execute(delete(Trip).where(Trip.id == trip_id))
            db.execute(
                delete(LoadPlanOrder).where(LoadPlanOrder.load_plan_id == plan_id)
            )
            db.execute(delete(LoadPlan).where(LoadPlan.id == plan_id))
            db.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
            db.execute(delete(Order).where(Order.id.in_(order_ids)))
            db.execute(delete(Product).where(Product.id == product_id))
            db.execute(delete(Customer).where(Customer.id == customer_id))
            db.execute(delete(Truck).where(Truck.id == truck_id))
            db.execute(delete(User).where(User.id == manager_id))
            db.execute(delete(Driver).where(Driver.id == driver_id))
            db.commit()
