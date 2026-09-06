import uuid
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer
from app.modules.drivers.models import Driver
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.schemas import (
    OrderCreate,
    OrderRead,
    OrderStatusChange,
    OrderUpdate,
)
from app.modules.orders.service import (
    OrderCustomerNotFoundError,
    OrderEditNotAllowedError,
    OrderItemsReferencedByLoadPlanError,
    OrderNotFoundError,
    OrderProductNotFoundError,
    OrderService,
    OrderStatusTransitionNotAllowedError,
)
from app.modules.products.models import Product
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.service import StatusHistoryChangedByNotFoundError
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
)


def create_manager(db: Session) -> User:
    manager = User(
        name="Gestor de Teste",
        email=f"manager-{uuid.uuid4()}@example.test",
        password_hash="hash-ficticio",
        role="LOGISTICS_MANAGER",
        active=True,
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return manager


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
        expected_delivery_at=datetime(
            2026, 8, 10, 10, 0, tzinfo=timezone(timedelta(hours=-3))
        ),
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


def test_order_read_normalizes_database_datetimes_to_utc() -> None:
    local_timezone = timezone(timedelta(hours=-3))

    data = OrderRead.model_validate(
        {
            "id": uuid.uuid4(),
            "customer_id": uuid.uuid4(),
            "status": "DRAFT",
            "priority": "NORMAL",
            "delivery_address": "Rua Exemplo, 100",
            "expected_delivery_at": datetime(2026, 8, 10, 10, 0, tzinfo=local_timezone),
            "created_at": datetime(2026, 8, 4, 20, 0, tzinfo=local_timezone),
            "items": [],
        }
    )

    assert data.expected_delivery_at == datetime(2026, 8, 10, 13, 0, tzinfo=UTC)
    assert data.created_at == datetime(2026, 8, 4, 23, 0, tzinfo=UTC)


def test_order_update_rejects_status_field() -> None:
    with pytest.raises(ValidationError):
        OrderUpdate(status="READY")


def test_order_rejects_different_delivery_sequences_in_the_same_order() -> None:
    with pytest.raises(ValidationError):
        OrderCreate(
            customer_id=uuid.uuid4(),
            priority="NORMAL",
            delivery_address="Rua Exemplo, 100",
            items=[
                {
                    "product_id": uuid.uuid4(),
                    "quantity": 1,
                    "delivery_sequence": 1,
                },
                {
                    "product_id": uuid.uuid4(),
                    "quantity": 1,
                    "delivery_sequence": 2,
                },
            ],
        )


def test_order_status_change_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        OrderStatusChange(status="invalid")


def test_create_order_persists_default_status_and_items(db_session: Session) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)

    order = service.create_order(
        make_order_create(customer.id, product.id), changed_by=manager.id
    )

    assert order.id is not None
    assert order.customer_id == customer.id
    assert order.status == "DRAFT"
    assert order.priority == "NORMAL"
    assert len(order.items) == 1
    assert order.items[0].product_id == product.id
    assert order.items[0].quantity == 3
    assert order.items[0].delivery_sequence == 1
    history = db_session.scalars(select(StatusHistory)).all()
    assert len(history) == 1
    assert history[0].entity_type == "ORDER"
    assert history[0].entity_id == order.id
    assert history[0].old_status is None
    assert history[0].new_status == "DRAFT"
    assert history[0].changed_by == manager.id


def test_create_order_rejects_missing_customer(db_session: Session) -> None:
    product = create_product(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)

    with pytest.raises(OrderCustomerNotFoundError):
        service.create_order(
            make_order_create(uuid.uuid4(), product.id), changed_by=manager.id
        )


def test_create_order_rejects_missing_product(db_session: Session) -> None:
    customer = create_customer(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)

    with pytest.raises(OrderProductNotFoundError) as exc_info:
        service.create_order(
            make_order_create(customer.id, uuid.uuid4()), changed_by=manager.id
        )

    assert len(exc_info.value.product_ids) == 1


def test_create_order_rolls_back_when_history_actor_does_not_exist(
    db_session: Session,
) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    service = OrderService(db_session)

    with pytest.raises(StatusHistoryChangedByNotFoundError):
        service.create_order(
            make_order_create(customer.id, product.id), changed_by=uuid.uuid4()
        )

    assert not db_session.in_transaction()
    assert db_session.scalars(select(Order)).all() == []
    assert db_session.scalars(select(StatusHistory)).all() == []


def test_update_order_replaces_items_and_normalizes_fields(db_session: Session) -> None:
    customer = create_customer(db_session)
    first_product = create_product(db_session, "CX-A")
    second_product = create_product(db_session, "CX-B")
    manager = create_manager(db_session)
    service = OrderService(db_session)
    order = service.create_order(
        make_order_create(customer.id, first_product.id), changed_by=manager.id
    )

    updated_order = service.update_order(
        order.id,
        OrderUpdate(
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

    assert updated_order.status == "DRAFT"
    assert updated_order.priority == "HIGH"
    assert len(updated_order.items) == 1
    assert updated_order.items[0].product_id == second_product.id
    assert updated_order.items[0].quantity == 2
    assert updated_order.items[0].delivery_sequence == 2


def test_get_order_raises_when_not_found(db_session: Session) -> None:
    service = OrderService(db_session)

    with pytest.raises(OrderNotFoundError):
        service.get_order(uuid.uuid4())


def test_update_order_rolls_back_validation_error_after_lock(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)
    order = service.create_order(
        make_order_create(customer.id, product.id), changed_by=manager.id
    )
    order_id = order.id
    monkeypatch.setattr(
        service.load_plan_reference_service,
        "has_order_item_references",
        lambda _identifiers: True,
    )

    with pytest.raises(OrderItemsReferencedByLoadPlanError):
        service.update_order(
            order_id,
            OrderUpdate(
                items=[
                    {
                        "product_id": product.id,
                        "quantity": 2,
                        "delivery_sequence": 1,
                    }
                ]
            ),
        )

    assert not db_session.in_transaction()
    persisted = service.get_order(order_id)
    assert len(persisted.items) == 1
    assert persisted.items[0].quantity == 3


@pytest.mark.parametrize(
    ("initial_status", "requested_status"),
    [
        ("DRAFT", "READY"),
        ("DRAFT", "CANCELED"),
        ("READY", "DRAFT"),
        ("READY", "CANCELED"),
    ],
)
def test_change_order_status_accepts_manual_transition_matrix(
    db_session: Session,
    initial_status: str,
    requested_status: str,
) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)
    order = service.create_order(
        make_order_create(customer.id, product.id), changed_by=manager.id
    )
    if initial_status == "READY":
        order = service.change_order_status(order.id, "READY", changed_by=manager.id)

    changed_order = service.change_order_status(
        order.id, requested_status.lower(), changed_by=manager.id
    )

    assert changed_order.status == requested_status
    history = db_session.scalars(
        select(StatusHistory).where(
            StatusHistory.entity_id == order.id,
            StatusHistory.old_status == initial_status,
            StatusHistory.new_status == requested_status,
        )
    ).all()
    assert len(history) == 1
    assert history[0].changed_by == manager.id


def test_change_order_status_is_idempotent_without_duplicate_history(
    db_session: Session,
) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)
    order = service.create_order(
        make_order_create(customer.id, product.id), changed_by=manager.id
    )

    unchanged_order = service.change_order_status(
        order.id, "draft", changed_by=manager.id
    )

    assert unchanged_order.status == "DRAFT"
    history = db_session.scalars(
        select(StatusHistory).where(StatusHistory.entity_id == order.id)
    ).all()
    assert len(history) == 1


def test_change_order_status_rejects_transition_reserved_for_plan_approval(
    db_session: Session,
) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)
    order = service.create_order(
        make_order_create(customer.id, product.id), changed_by=manager.id
    )

    with pytest.raises(OrderStatusTransitionNotAllowedError):
        service.change_order_status(order.id, "PLANNED", changed_by=manager.id)

    assert service.get_order(order.id).status == "DRAFT"
    history = db_session.scalars(
        select(StatusHistory).where(StatusHistory.entity_id == order.id)
    ).all()
    assert len(history) == 1


def test_update_order_rejects_edit_after_draft(db_session: Session) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)
    order = service.create_order(
        make_order_create(customer.id, product.id), changed_by=manager.id
    )
    service.change_order_status(order.id, "READY", changed_by=manager.id)

    with pytest.raises(OrderEditNotAllowedError):
        service.update_order(order.id, OrderUpdate(priority="HIGH"))

    assert service.get_order(order.id).priority == "NORMAL"


def test_status_transition_rolls_back_order_when_history_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    customer = create_customer(db_session)
    product = create_product(db_session)
    manager = create_manager(db_session)
    service = OrderService(db_session)
    order = service.create_order(
        make_order_create(customer.id, product.id), changed_by=manager.id
    )
    monkeypatch.setattr(
        service.status_history_service,
        "stage_status_change",
        lambda _data: (_ for _ in ()).throw(RuntimeError("history failure")),
    )

    with pytest.raises(RuntimeError, match="history failure"):
        service.change_order_status(order.id, "READY", changed_by=manager.id)

    assert not db_session.in_transaction()
    assert service.get_order(order.id).status == "DRAFT"
    history = db_session.scalars(
        select(StatusHistory).where(StatusHistory.entity_id == order.id)
    ).all()
    assert len(history) == 1
