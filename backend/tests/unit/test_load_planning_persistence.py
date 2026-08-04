import uuid
from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.modules.customers.models import Customer
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.load_planning.repository import LoadPlanRepository
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.trucks.models import Truck


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    tables = [
        Customer.__table__,
        Truck.__table__,
        Product.__table__,
        Order.__table__,
        OrderItem.__table__,
        LoadPlan.__table__,
        LoadPlanOrder.__table__,
        LoadPlanItem.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=list(reversed(tables)))


def seed_sources(db: Session) -> tuple[Truck, Product, Order, OrderItem]:
    customer = Customer(
        id=uuid.uuid4(),
        name="Cliente de Persistencia",
        document="00000000000191",
        address="Rua Exemplo, 100",
        city="Sao Paulo",
        state="SP",
    )
    truck = Truck(
        id=uuid.uuid4(),
        plate="ABC1D23",
        model="Bau de teste",
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=Decimal("1000.00"),
        active=True,
    )
    product = Product(
        id=uuid.uuid4(),
        code="CX-A",
        name="Caixa A",
        width_cm=10,
        height_cm=10,
        length_cm=10,
        weight_kg=Decimal("1.000"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )
    order = Order(
        id=uuid.uuid4(),
        customer_id=customer.id,
        status="READY",
        priority="NORMAL",
        delivery_address="Rua Exemplo, 100",
    )
    order_item = OrderItem(
        id=uuid.uuid4(),
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        delivery_sequence=1,
    )
    db.add_all((customer, truck, product, order, order_item))
    db.commit()
    return truck, product, order, order_item


def make_load_plan(
    truck: Truck,
    product: Product,
    order: Order,
    order_item: OrderItem,
) -> LoadPlan:
    return LoadPlan(
        truck_id=truck.id,
        status="CALCULATED",
        truck_snapshot_plate=truck.plate,
        truck_snapshot_model=truck.model,
        truck_snapshot_internal_width_cm=truck.internal_width_cm,
        truck_snapshot_internal_height_cm=truck.internal_height_cm,
        truck_snapshot_internal_length_cm=truck.internal_length_cm,
        truck_snapshot_max_weight_kg=truck.max_weight_kg,
        internal_volume_cm3=1_000_000,
        used_volume_cm3=1_000,
        occupancy_percent=Decimal("0.10"),
        total_weight_kg=Decimal("1.000"),
        loaded_count=1,
        unloaded_count=0,
        algorithm_version="heuristic-v1",
        orders=[LoadPlanOrder(order_id=order.id)],
        items=[
            LoadPlanItem(
                order_id=order.id,
                order_item_id=order_item.id,
                product_id=product.id,
                volume_index=1,
                order_item_snapshot_quantity=order_item.quantity,
                order_item_snapshot_delivery_sequence=order_item.delivery_sequence,
                product_snapshot_code=product.code,
                product_snapshot_name=product.name,
                product_snapshot_width_cm=product.width_cm,
                product_snapshot_height_cm=product.height_cm,
                product_snapshot_length_cm=product.length_cm,
                product_snapshot_weight_kg=product.weight_kg,
                product_snapshot_fragile=product.fragile,
                product_snapshot_stackable=product.stackable,
                product_snapshot_rotation_allowed=product.rotation_allowed,
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
        ],
    )


def constraint_names(table, constraint_type: type) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type) and constraint.name is not None
    }


def test_load_planning_tables_and_constraints_are_registered() -> None:
    assert "volumes" not in Base.metadata.tables
    assert LoadPlan.__table__ is Base.metadata.tables["load_plans"]
    assert LoadPlanOrder.__table__ is Base.metadata.tables["load_plan_orders"]
    assert LoadPlanItem.__table__ is Base.metadata.tables["load_plan_items"]

    assert {
        "ck_load_plans__status_allowed",
        "ck_load_plans__approval_consistent",
        "ck_load_plans__status_metrics_consistent",
        "ck_load_plans__internal_volume_matches_snapshot",
    } <= constraint_names(LoadPlan.__table__, CheckConstraint)
    assert {
        "ck_load_plan_items__placed_or_rejected",
        "ck_load_plan_items__rotation_code_allowed",
        "ck_load_plan_items__rotation_permission_consistent",
        "ck_load_plan_items__rotation_dimensions_consistent",
        "ck_load_plan_items__rejection_reason_allowed",
        "ck_load_plan_items__volume_index_within_snapshot_quantity",
    } <= constraint_names(LoadPlanItem.__table__, CheckConstraint)
    assert {
        "uq_load_plan_items__plan_item_volume",
        "uq_load_plan_items__plan_loading_sequence",
    } <= constraint_names(LoadPlanItem.__table__, UniqueConstraint)
    assert "uq_order_items__id_order_product" in constraint_names(
        OrderItem.__table__, UniqueConstraint
    )


def test_provenance_foreign_keys_are_restrictive() -> None:
    expected_foreign_keys = {
        "fk_load_plan_items__load_plans",
        "fk_load_plan_items__load_plan_orders",
        "fk_load_plan_items__orders",
        "fk_load_plan_items__order_items",
        "fk_load_plan_items__order_item_provenance",
        "fk_load_plan_items__products",
    }
    foreign_keys = [
        constraint
        for constraint in LoadPlanItem.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert {constraint.name for constraint in foreign_keys} == expected_foreign_keys
    assert all(constraint.ondelete == "RESTRICT" for constraint in foreign_keys)


def test_item_order_must_belong_to_the_plan(db_session: Session) -> None:
    truck, product, order, order_item = seed_sources(db_session)
    other_order = Order(
        id=uuid.uuid4(),
        customer_id=order.customer_id,
        status="READY",
        priority="NORMAL",
        delivery_address="Rua Exemplo, 200",
    )
    other_item = OrderItem(
        id=uuid.uuid4(),
        order_id=other_order.id,
        product_id=product.id,
        quantity=1,
        delivery_sequence=2,
    )
    db_session.add_all((other_order, other_item))
    db_session.commit()
    plan = make_load_plan(truck, product, order, order_item)
    plan.items[0].order_id = other_order.id
    plan.items[0].order_item_id = other_item.id

    with pytest.raises(IntegrityError):
        LoadPlanRepository(db_session).add(plan)
    db_session.rollback()


def test_item_order_and_product_must_match_order_item(db_session: Session) -> None:
    truck, product, order, order_item = seed_sources(db_session)
    other_product = Product(
        id=uuid.uuid4(),
        code="CX-B",
        name="Caixa B",
        width_cm=10,
        height_cm=10,
        length_cm=10,
        weight_kg=Decimal("1.000"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )
    other_order = Order(
        id=uuid.uuid4(),
        customer_id=order.customer_id,
        status="READY",
        priority="NORMAL",
        delivery_address="Rua Exemplo, 300",
    )
    db_session.add_all((other_product, other_order))
    db_session.commit()

    for field_name, inconsistent_id in (
        ("order_id", other_order.id),
        ("product_id", other_product.id),
    ):
        plan = make_load_plan(truck, product, order, order_item)
        plan.orders.append(LoadPlanOrder(order_id=other_order.id))
        setattr(plan.items[0], field_name, inconsistent_id)

        with pytest.raises(IntegrityError):
            LoadPlanRepository(db_session).add(plan)
        db_session.rollback()


def test_repository_persists_and_eagerly_loads_complete_snapshot(
    db_session: Session,
) -> None:
    truck, product, order, order_item = seed_sources(db_session)
    repository = LoadPlanRepository(db_session)
    plan = repository.add(make_load_plan(truck, product, order, order_item))
    plan_id = plan.id
    order_id = order.id
    order_item_id = order_item.id
    db_session.commit()
    db_session.expunge_all()

    persisted = repository.get(plan_id)

    assert persisted is not None
    assert persisted.truck_snapshot_plate == "ABC1D23"
    assert persisted.internal_volume_cm3 == 1_000_000
    assert persisted.used_volume_cm3 == 1_000
    assert [association.order_id for association in persisted.orders] == [order_id]
    assert len(persisted.items) == 1
    assert persisted.items[0].order_item_id == order_item_id
    assert persisted.items[0].product_snapshot_name == "Caixa A"


def test_referenced_order_item_cannot_be_deleted(db_session: Session) -> None:
    truck, product, order, order_item = seed_sources(db_session)
    repository = LoadPlanRepository(db_session)
    repository.add(make_load_plan(truck, product, order, order_item))
    db_session.commit()

    db_session.delete(order_item)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.get(OrderItem, order_item.id) is not None


def test_snapshot_rotation_permission_is_enforced(db_session: Session) -> None:
    truck, product, order, order_item = seed_sources(db_session)
    product.rotation_allowed = False
    db_session.commit()
    plan = make_load_plan(truck, product, order, order_item)
    plan.items[0].rotation_code = "XZY"

    with pytest.raises(IntegrityError):
        LoadPlanRepository(db_session).add(plan)
    db_session.rollback()


def test_placed_item_cannot_carry_rejection_reason(db_session: Session) -> None:
    truck, product, order, order_item = seed_sources(db_session)
    plan = make_load_plan(truck, product, order, order_item)
    plan.items[0].rejection_reason = "COLLISION"

    with pytest.raises(IntegrityError):
        LoadPlanRepository(db_session).add(plan)
    db_session.rollback()
