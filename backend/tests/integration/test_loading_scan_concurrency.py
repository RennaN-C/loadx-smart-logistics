from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from app.modules.customers.models import Customer
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.loading.models import LoadingSession, LoadingSessionItem
from app.modules.loading.service import LoadingItemAlreadyCheckedError, LoadingService
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.trucks.models import Truck
from tests.unit.test_loading_service import seed_plan


def test_concurrent_scans_refresh_stale_items_and_check_once(postgres_engine):
    factory = sessionmaker(bind=postgres_engine, autoflush=False)
    with factory() as db:
        plan = seed_plan(db)
        plan_id, truck_id = plan.id, plan.truck_id
        order = db.get(Order, plan.orders[0].order_id)
        order_id, customer_id, product_id = (
            order.id,
            order.customer_id,
            order.items[0].product_id,
        )
        service = LoadingService(db)
        loading = service.create_session(plan_id)
        service.change_status(loading.id, "IN_PROGRESS")
        session_id, item_id = loading.id, loading.items[0].id
    barrier = Barrier(2)

    def scan():
        with factory() as db:
            assert db.get(LoadingSessionItem, item_id).status == "PENDING"
            barrier.wait(timeout=5)
            try:
                LoadingService(db).scan_item(session_id, item_id)
                return "checked"
            except LoadingItemAlreadyCheckedError:
                db.rollback()
                return "duplicate"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(scan) for _ in range(2)]
            assert sorted(future.result(timeout=15) for future in futures) == [
                "checked",
                "duplicate",
            ]
        with factory() as db:
            loading = LoadingService(db).get_session(session_id)
            assert sum(item.status == "CHECKED" for item in loading.items) == 1
            assert loading.status == "IN_PROGRESS"
    finally:
        with factory() as db:
            for model, condition in (
                (
                    LoadingSessionItem,
                    LoadingSessionItem.loading_session_id == session_id,
                ),
                (LoadingSession, LoadingSession.id == session_id),
                (LoadPlanItem, LoadPlanItem.load_plan_id == plan_id),
                (LoadPlanOrder, LoadPlanOrder.load_plan_id == plan_id),
                (LoadPlan, LoadPlan.id == plan_id),
                (OrderItem, OrderItem.order_id == order_id),
                (Order, Order.id == order_id),
                (Product, Product.id == product_id),
                (Customer, Customer.id == customer_id),
                (Truck, Truck.id == truck_id),
            ):
                db.execute(delete(model).where(condition))
            db.commit()
