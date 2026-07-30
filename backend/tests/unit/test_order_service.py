import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.schemas import OrderCreate, OrderUpdate
from app.modules.orders.service import (
    OrderCustomerNotFoundError,
    OrderNotFoundError,
    OrderProductNotFoundError,
    OrderService,
)
from app.modules.products.models import Product


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [Customer.__table__, Product.__table__, Order.__table__, OrderItem.__table__]
    Base.metadata.create_all(engine, tables=tables)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=list(reversed(tables)))


def create_customer(db: Session) -> Customer:
    customer = Customer(
        name="Cliente Demonstracao",
        document="00000000000191",
        phone="5500000000000",
        address="Rua Exemplo, 100",
        city="Sao Paulo",
        state="SP",
        notes="Cliente ficticio para testes",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_product(db: Session, code: str = "CX-A") -> Product:
    product = Product(
        code=code,
        name=f"Produto {code}",
        description="Produto ficticio para testes",
        width_cm=60,
        height_cm=50,
        length_cm=40,
        weight_kg=Decimal("12.500"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def make_order_create(customer_id: uuid.UUID, product_id: uuid.UUID) -> OrderCreate:
    return OrderCreate(
        customer_id=customer_id,
        priority="normal",
        delivery_address="Rua Exemplo, 100",
        expected_delivery_at=datetime(2026, 8, 10, 10, 0, tzinfo=timezone(timedelta(hours=-3))),
        items=[
            {
                "product_id": product_id,
                "quantity": 3,
                "delivery_sequence": 1,
            }
        ],
    )


def test_order_create_normalizes_priority_and_expected_delivery_at() -> None:
    customer_id = uuid.uuid4()
    product_id = uuid.uuid4()

    data = make_order_create(customer_id, product_id)

    assert data.priority == "NORMAL"
    assert data.expected_delivery_at == datetime(2026, 8, 10, 13, 0, tzinfo=UTC)


def test_order_update_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        OrderUpdate(status="invalid")


def test_create_order_persists_default_status_and_items(db_session: Session) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    service = OrderService(db_session)

    order = service.create_order(make_order_create(customer.id, product.id))

    assert order.id is not None
    assert order.customer_id == customer.id
    assert order.status == "DRAFT"
    assert order.priority == "NORMAL"
    assert len(order.items) == 1
    assert order.items[0].product_id == product.id
    assert order.items[0].quantity == 3
    assert order.items[0].delivery_sequence == 1


def test_create_order_rejects_missing_customer(db_session: Session) -> None:
    product = create_product(db_session)
    service = OrderService(db_session)

    with pytest.raises(OrderCustomerNotFoundError):
        service.create_order(make_order_create(uuid.uuid4(), product.id))


def test_create_order_rejects_missing_product(db_session: Session) -> None:
    customer = create_customer(db_session)
    service = OrderService(db_session)

    with pytest.raises(OrderProductNotFoundError) as exc_info:
        service.create_order(make_order_create(customer.id, uuid.uuid4()))

    assert len(exc_info.value.product_ids) == 1


def test_update_order_replaces_items_and_normalizes_fields(db_session: Session) -> None:
    customer = create_customer(db_session)
    first_product = create_product(db_session, "CX-A")
    second_product = create_product(db_session, "CX-B")
    service = OrderService(db_session)
    order = service.create_order(make_order_create(customer.id, first_product.id))

    updated_order = service.update_order(
        order.id,
        OrderUpdate(
            status="ready",
            priority="high",
            items=[
                {
                    "product_id": second_product.id,
                    "quantity": 2,
                    "delivery_sequence": 2,
                }
            ],
        ),
    )

    assert updated_order.status == "READY"
    assert updated_order.priority == "HIGH"
    assert len(updated_order.items) == 1
    assert updated_order.items[0].product_id == second_product.id
    assert updated_order.items[0].quantity == 2
    assert updated_order.items[0].delivery_sequence == 2


def test_get_order_raises_when_not_found(db_session: Session) -> None:
    service = OrderService(db_session)

    with pytest.raises(OrderNotFoundError):
        service.get_order(uuid.uuid4())
