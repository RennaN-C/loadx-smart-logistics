import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.loading.models import LoadingSession, LoadingSessionItem
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.loading.service import (
    LoadingChecklistIncompleteError,
    LoadingPlanNotApprovedError,
    LoadingService,
    LoadingStatusTransitionError,
)
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.trucks.models import Truck

SQLITE_TABLES = (
    Customer.__table__,
    Truck.__table__,
    Product.__table__,
    Order.__table__,
    OrderItem.__table__,
    LoadPlan.__table__,
    LoadPlanOrder.__table__,
    LoadPlanItem.__table__,
    LoadingSession.__table__,
    LoadingSessionItem.__table__,
)


def seed_plan(db: Session, *, status: str = "APPROVED") -> LoadPlan:
    customer = Customer(
        name="Cliente Loading",
        document=uuid.uuid4().hex,
        address="Rua de Teste, 100",
        city="Sao Paulo",
        state="SP",
    )
    truck = Truck(
        plate=f"L{uuid.uuid4().hex[:6]}",
        model="Bau loading",
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=Decimal("1000.00"),
        active=True,
    )
    product = Product(
        code=f"LOAD-{uuid.uuid4().hex}",
        name="Caixa loading",
        width_cm=10,
        height_cm=10,
        length_cm=10,
        weight_kg=Decimal("1.000"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )
    db.add_all((customer, truck, product))
    db.flush()
    order = Order(
        customer_id=customer.id,
        status="PLANNED" if status == "APPROVED" else "READY",
        priority="NORMAL",
        delivery_address="Rua de Teste, 200",
        items=[OrderItem(product_id=product.id, quantity=2, delivery_sequence=1)],
    )
    db.add(order)
    db.flush()
    order_item = order.items[0]
    plan = LoadPlan(
        truck_id=truck.id,
        status=status,
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
        algorithm_version="loading-test-v1",
        approved_at=datetime.now(UTC) if status == "APPROVED" else None,
        orders=[LoadPlanOrder(order_id=order.id)],
    )
    db.add(plan)
    db.flush()
    plan.items = [
        LoadPlanItem(
            order_id=order.id,
            order_item_id=order_item.id,
            product_id=product.id,
            volume_index=index,
            order_item_snapshot_quantity=2,
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
            position_x_cm=(index - 1) * 10,
            position_y_cm=0,
            position_z_cm=0,
            used_width_cm=10,
            used_height_cm=10,
            used_length_cm=10,
            rotation_code="XYZ",
            loading_sequence=index,
            placed=True,
        )
        for index in (1, 2)
    ]
    db.commit()
    return plan


def test_loading_requires_approved_existing_plan(db_session: Session) -> None:
    service = LoadingService(db_session)

    with pytest.raises(LoadingPlanNotApprovedError):
        service.create_session(uuid.uuid4())

    calculated_plan = seed_plan(db_session, status="CALCULATED")
    with pytest.raises(LoadingPlanNotApprovedError):
        service.create_session(calculated_plan.id)


def test_complete_loading_flow_releases_only_its_plan(db_session: Session) -> None:
    plan = seed_plan(db_session)
    other_plan = seed_plan(db_session)
    service = LoadingService(db_session)
    reference = LoadingReferenceService(db_session)
    loading = service.create_session(plan.id)

    assert loading.status == "PENDING"
    assert len(loading.items) == 2
    assert not reference.is_load_plan_finished(plan.id)
    assert not reference.is_load_plan_finished(other_plan.id)
    assert not reference.is_load_plan_finished(uuid.uuid4())

    with pytest.raises(LoadingStatusTransitionError):
        service.change_status(loading.id, "FINISHED")

    loading = service.change_status(loading.id, "IN_PROGRESS")
    assert loading.started_at is not None
    with pytest.raises(LoadingChecklistIncompleteError):
        service.change_status(loading.id, "FINISHED")

    for item in loading.items:
        loading = service.change_item_status(loading.id, item.id, "CHECKED")

    loading = service.change_status(loading.id, "FINISHED")
    assert loading.finished_at is not None
    assert all(item.status == "CHECKED" for item in loading.items)
    assert reference.is_load_plan_finished(plan.id)
    assert not reference.is_load_plan_finished(other_plan.id)
