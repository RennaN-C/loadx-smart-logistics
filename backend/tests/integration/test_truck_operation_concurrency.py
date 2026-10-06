import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.modules.customers.models import Customer
from app.modules.load_planning.models import (
    LoadPlan,
    LoadPlanItem,
    LoadPlanOrder,
)
from app.modules.loading.models import LoadingSession, LoadingSessionItem
from app.modules.loading.service import LoadingService
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.trucks.models import Truck
from app.modules.trucks.service import TruckOperationConflictError


def _create_plan(
    db: Session,
    *,
    truck: Truck,
) -> tuple[LoadPlan, Order, Product, Customer]:
    customer = Customer(
        name="Cliente concorrencia",
        document=uuid.uuid4().hex,
        address="Rua Concorrencia, 100",
        city="Sao Paulo",
        state="SP",
    )
    product = Product(
        code=f"CONC-{uuid.uuid4().hex}",
        name="Produto concorrencia",
        width_cm=10,
        height_cm=10,
        length_cm=10,
        weight_kg=Decimal("1.000"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )

    db.add_all((customer, product))
    db.flush()

    order = Order(
        customer_id=customer.id,
        status="PLANNED",
        priority="NORMAL",
        delivery_address="Rua Concorrencia, 200",
        items=[
            OrderItem(
                product_id=product.id,
                quantity=1,
                delivery_sequence=1,
            )
        ],
    )
    db.add(order)
    db.flush()

    order_item = order.items[0]

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
        used_volume_cm3=1_000,
        occupancy_percent=Decimal("0.10"),
        total_weight_kg=Decimal("1.000"),
        loaded_count=1,
        unloaded_count=0,
        algorithm_version="concurrency-test-v1",
        approved_at=datetime.now(UTC),
        orders=[LoadPlanOrder(order_id=order.id)],
    )

    db.add(plan)
    db.flush()

    plan.items = [
        LoadPlanItem(
            order_id=order.id,
            order_item_id=order_item.id,
            product_id=product.id,
            volume_index=1,
            order_item_snapshot_quantity=1,
            order_item_snapshot_delivery_sequence=1,
            product_snapshot_code=product.code,
            product_snapshot_name=product.name,
            product_snapshot_width_cm=10,
            product_snapshot_height_cm=10,
            product_snapshot_length_cm=10,
            product_snapshot_weight_kg=Decimal("1.000"),
            product_snapshot_fragile=False,
            product_snapshot_stackable=True,
            product_snapshot_rotation_allowed=True,
            position_x_cm=0,
            position_y_cm=0,
            position_z_cm=0,
            used_width_cm=10,
            used_height_cm=10,
            used_length_cm=10,
            rotation_code="XYZ",
            loading_sequence=1,
            placed=True,
        )
    ]

    db.flush()
    return plan, order, product, customer


def test_concurrent_truck_reservation_allows_only_one_operation(
    postgres_engine: Engine,
) -> None:
    session_factory = sessionmaker(
        bind=postgres_engine,
        autoflush=False,
        autocommit=False,
    )

    with session_factory() as db:
        truck = Truck(
            plate=f"C{uuid.uuid4().hex[:6]}",
            model="Caminhao concorrencia",
            internal_width_cm=100,
            internal_height_cm=100,
            internal_length_cm=100,
            max_weight_kg=Decimal("1000.00"),
            active=True,
        )
        db.add(truck)
        db.flush()

        first_plan, first_order, first_product, first_customer = _create_plan(
            db,
            truck=truck,
        )
        second_plan, second_order, second_product, second_customer = _create_plan(
            db,
            truck=truck,
        )

        truck_id = truck.id
        plan_ids = (first_plan.id, second_plan.id)
        order_ids = (first_order.id, second_order.id)
        product_ids = (first_product.id, second_product.id)
        customer_ids = (first_customer.id, second_customer.id)

        db.commit()

    barrier = Barrier(2)

    def reserve(plan_id: uuid.UUID) -> str:
        with session_factory() as db:
            barrier.wait(timeout=5)
            try:
                LoadingService(db).create_session(plan_id)
            except TruckOperationConflictError:
                return "CONFLICT"
            return "CREATED"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(reserve, plan_id) for plan_id in plan_ids]
            results = [future.result(timeout=15) for future in futures]

        assert sorted(results) == ["CONFLICT", "CREATED"]

        with session_factory() as db:
            sessions = db.scalars(
                select(LoadingSession).where(LoadingSession.load_plan_id.in_(plan_ids))
            ).all()

            assert len(sessions) == 1
            assert sessions[0].load_plan_id in plan_ids

    finally:
        with session_factory() as db:
            loading_session_ids = tuple(
                db.scalars(
                    select(LoadingSession.id).where(
                        LoadingSession.load_plan_id.in_(plan_ids)
                    )
                ).all()
            )

            if loading_session_ids:
                db.execute(
                    delete(LoadingSessionItem).where(
                        LoadingSessionItem.loading_session_id.in_(loading_session_ids)
                    )
                )

            db.execute(
                delete(LoadingSession).where(LoadingSession.load_plan_id.in_(plan_ids))
            )
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
            db.execute(delete(Truck).where(Truck.id == truck_id))
            db.commit()
