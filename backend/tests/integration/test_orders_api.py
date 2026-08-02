import uuid
from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate
from app.modules.customers.service import CustomerService
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate
from app.modules.products.service import ProductService

SessionFactory = Callable[[], Session]


@pytest.fixture
def session_factory() -> Generator[SessionFactory, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        Customer.__table__,
        Product.__table__,
        Order.__table__,
        OrderItem.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield testing_session_local
    finally:
        Base.metadata.drop_all(engine, tables=list(reversed(tables)))


@pytest.fixture
def client(session_factory: SessionFactory) -> Generator[TestClient, None, None]:

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def create_customer(session_factory: SessionFactory) -> str:
    db = session_factory()
    try:
        customer = CustomerService(db).create_customer(
            CustomerCreate(
                name="Cliente Demonstracao",
                document=uuid.uuid4().hex,
                phone="5500000000000",
                address="Rua Exemplo, 100",
                city="Sao Paulo",
                state="SP",
                notes="Cliente ficticio para testes",
            )
        )
        return str(customer.id)
    finally:
        db.close()


def create_product(
    session_factory: SessionFactory,
    code: str = "CX-A",
) -> str:
    db = session_factory()
    try:
        product = ProductService(db).create_product(
            ProductCreate(
                code=code,
                name=f"Produto {code}",
                description="Produto ficticio para testes",
                width_cm=60,
                height_cm=50,
                length_cm=40,
                weight_kg=12.5,
                fragile=False,
                stackable=True,
                rotation_allowed=True,
            )
        )
        return str(product.id)
    finally:
        db.close()


def make_order_payload(customer_id: str, product_id: str) -> dict[str, object]:
    return {
        "customer_id": customer_id,
        "priority": "normal",
        "delivery_address": "Rua Exemplo, 100",
        "expected_delivery_at": "2026-08-10T10:00:00-03:00",
        "items": [
            {
                "product_id": product_id,
                "quantity": 3,
                "delivery_sequence": 1,
            }
        ],
    }


def create_order(
    client: TestClient,
    session_factory: SessionFactory,
) -> dict[str, object]:
    customer_id = create_customer(session_factory)
    product_id = create_product(session_factory)
    response = client.post(
        "/api/v1/orders", json=make_order_payload(customer_id, product_id)
    )
    assert response.status_code == 201
    return response.json()


def test_create_order_returns_created_resource(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    customer_id = create_customer(session_factory)
    product_id = create_product(session_factory)

    response = client.post(
        "/api/v1/orders", json=make_order_payload(customer_id, product_id)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["customer_id"] == customer_id
    assert body["status"] == "DRAFT"
    assert body["priority"] == "NORMAL"
    assert body["expected_delivery_at"].startswith("2026-08-10T13:00:00")
    assert body["items"][0]["product_id"] == product_id
    assert body["items"][0]["quantity"] == 3


def test_list_orders_returns_created_items(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    order = create_order(client, session_factory)

    response = client.get("/api/v1/orders")

    assert response.status_code == 200
    assert response.json()[0]["id"] == order["id"]


def test_get_order_by_id_returns_created_item(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    order = create_order(client, session_factory)

    response = client.get(f"/api/v1/orders/{order['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == order["id"]


def test_patch_order_updates_header_and_replaces_items(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    order = create_order(client, session_factory)
    second_product_id = create_product(session_factory, "CX-B")

    response = client.patch(
        f"/api/v1/orders/{order['id']}",
        json={
            "status": "ready",
            "priority": "high",
            "delivery_address": "Avenida Exemplo, 200",
            "items": [
                {
                    "product_id": second_product_id,
                    "quantity": 2,
                    "delivery_sequence": 2,
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "READY"
    assert body["priority"] == "HIGH"
    assert body["delivery_address"] == "Avenida Exemplo, 200"
    assert len(body["items"]) == 1
    assert body["items"][0]["product_id"] == second_product_id
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["delivery_sequence"] == 2


def test_patch_order_rejects_null_required_field_with_standard_error(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    order = create_order(client, session_factory)

    response = client.patch(f"/api/v1/orders/{order['id']}", json={"priority": None})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert body["details"][0]["field"] == "priority"


def test_patch_order_accepts_null_nullable_field(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    order = create_order(client, session_factory)

    response = client.patch(
        f"/api/v1/orders/{order['id']}",
        json={"expected_delivery_at": None},
    )

    assert response.status_code == 200
    assert response.json()["expected_delivery_at"] is None
    assert response.json()["priority"] == "NORMAL"


def test_create_order_returns_standard_error_for_missing_customer(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    product_id = create_product(session_factory)

    response = client.post(
        "/api/v1/orders", json=make_order_payload(str(uuid.uuid4()), product_id)
    )

    assert response.status_code == 404
    assert response.json() == {
        "code": "ORDER_CUSTOMER_NOT_FOUND",
        "message": "Cliente do pedido não encontrado.",
        "details": [{"field": "customer_id"}],
    }


def test_create_order_returns_standard_error_for_missing_product(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    customer_id = create_customer(session_factory)
    missing_product_id = str(uuid.uuid4())

    response = client.post(
        "/api/v1/orders", json=make_order_payload(customer_id, missing_product_id)
    )

    assert response.status_code == 404
    assert response.json() == {
        "code": "ORDER_PRODUCT_NOT_FOUND",
        "message": "Produto do pedido não encontrado.",
        "details": [{"field": "items.product_id", "ids": [missing_product_id]}],
    }


def test_create_order_rejects_empty_items(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    customer_id = create_customer(session_factory)
    product_id = create_product(session_factory)
    payload = make_order_payload(customer_id, product_id)
    payload["items"] = []

    response = client.post("/api/v1/orders", json=payload)

    assert response.status_code == 422


def test_patch_order_rejects_invalid_status(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    order = create_order(client, session_factory)

    response = client.patch(f"/api/v1/orders/{order['id']}", json={"status": "invalid"})

    assert response.status_code == 422
