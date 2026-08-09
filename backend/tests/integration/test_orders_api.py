import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.modules.customers.schemas import CustomerCreate
from app.modules.customers.service import CustomerService
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate
from app.modules.orders.service import OrderService
from app.modules.products.schemas import ProductCreate
from app.modules.products.service import ProductService
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.service import StatusHistoryService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService

SessionFactory = Callable[[], Session]
ORDER_ROUTE_CASES = [
    ("GET", "collection"),
    ("POST", "collection"),
    ("GET", "detail"),
    ("PATCH", "detail"),
    ("PATCH", "status"),
]


def create_user_in_db(
    session_factory: SessionFactory,
    email: str,
    role: str,
    active: bool = True,
) -> User:
    db = session_factory()
    try:
        return UserService(db).create_user(
            UserCreate(
                name="Usuário de Teste",
                email=email,
                password="senha-local-segura",
                role=role,
                active=active,
            )
        )
    finally:
        db.close()


def authorization_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id), {"role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(session_factory: SessionFactory) -> dict[str, str]:
    manager = create_user_in_db(
        session_factory,
        "manager@example.test",
        "LOGISTICS_MANAGER",
    )
    return authorization_headers(manager)


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
    headers: dict[str, str],
) -> dict[str, object]:
    customer_id = create_customer(session_factory)
    product_id = create_product(session_factory)
    response = client.post(
        "/api/v1/orders",
        json=make_order_payload(customer_id, product_id),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def create_order_in_db(session_factory: SessionFactory) -> Order:
    customer_id = create_customer(session_factory)
    product_id = create_product(session_factory)
    actor = create_user_in_db(
        session_factory,
        f"setup-manager-{uuid.uuid4()}@example.test",
        "LOGISTICS_MANAGER",
    )
    db = session_factory()
    try:
        return OrderService(db).create_order(
            OrderCreate.model_validate(make_order_payload(customer_id, product_id)),
            changed_by=actor.id,
        )
    finally:
        db.close()


def request_order_route(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
    order: Order,
    headers: dict[str, str] | None = None,
):
    path = "/api/v1/orders"
    if route == "detail":
        path = f"{path}/{order.id}"
    elif route == "status":
        path = f"{path}/{order.id}/status"

    payload = None
    if method == "POST":
        customer_id = create_customer(session_factory)
        product_id = create_product(session_factory, "CX-B")
        payload = make_order_payload(customer_id, product_id)
    elif method == "PATCH":
        payload = {"status": "READY"} if route == "status" else {"priority": "high"}

    request_options: dict[str, object] = {}
    if payload is not None:
        request_options["json"] = payload
    if headers is not None:
        request_options["headers"] = headers
    return client.request(method, path, **request_options)


def test_create_order_returns_created_resource(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    customer_id = create_customer(session_factory)
    product_id = create_product(session_factory)

    response = client.post(
        "/api/v1/orders",
        json=make_order_payload(customer_id, product_id),
        headers=manager_headers,
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
    db = session_factory()
    try:
        manager = db.scalar(select(User).where(User.email == "manager@example.test"))
        history = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id == uuid.UUID(body["id"])
            )
        ).all()
        assert manager is not None
        assert len(history) == 1
        assert history[0].entity_type == "ORDER"
        assert history[0].old_status is None
        assert history[0].new_status == "DRAFT"
        assert history[0].changed_by == manager.id
    finally:
        db.close()


def test_list_orders_returns_created_items(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)

    response = client.get("/api/v1/orders", headers=manager_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    listed_order = body["items"][0]
    assert listed_order["id"] == order["id"]
    assert listed_order["item_count"] == 1
    assert "delivery_address" not in listed_order
    assert "items" not in listed_order


def test_get_order_by_id_returns_created_item(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)

    response = client.get(
        f"/api/v1/orders/{order['id']}",
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == order["id"]


def test_patch_order_updates_header_and_replaces_items(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)
    second_product_id = create_product(session_factory, "CX-B")

    response = client.patch(
        f"/api/v1/orders/{order['id']}",
        json={
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
        headers=manager_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DRAFT"
    assert body["priority"] == "HIGH"
    assert body["delivery_address"] == "Avenida Exemplo, 200"
    assert len(body["items"]) == 1
    assert body["items"][0]["product_id"] == second_product_id
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["delivery_sequence"] == 2


def test_patch_order_rejects_null_required_field_with_standard_error(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)

    response = client.patch(
        f"/api/v1/orders/{order['id']}",
        json={"priority": None},
        headers=manager_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert body["details"][0]["field"] == "priority"


def test_patch_order_accepts_null_nullable_field(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)

    response = client.patch(
        f"/api/v1/orders/{order['id']}",
        json={"expected_delivery_at": None},
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["expected_delivery_at"] is None
    assert response.json()["priority"] == "NORMAL"


def test_create_order_returns_standard_error_for_missing_customer(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    product_id = create_product(session_factory)

    response = client.post(
        "/api/v1/orders",
        json=make_order_payload(str(uuid.uuid4()), product_id),
        headers=manager_headers,
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
    manager_headers: dict[str, str],
) -> None:
    customer_id = create_customer(session_factory)
    missing_product_id = str(uuid.uuid4())

    response = client.post(
        "/api/v1/orders",
        json=make_order_payload(customer_id, missing_product_id),
        headers=manager_headers,
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
    manager_headers: dict[str, str],
) -> None:
    customer_id = create_customer(session_factory)
    product_id = create_product(session_factory)
    payload = make_order_payload(customer_id, product_id)
    payload["items"] = []

    response = client.post(
        "/api/v1/orders",
        json=payload,
        headers=manager_headers,
    )

    assert response.status_code == 422


def test_generic_patch_order_rejects_status_field(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)

    response = client.patch(
        f"/api/v1/orders/{order['id']}",
        json={"status": "READY"},
        headers=manager_headers,
    )

    assert response.status_code == 422


def test_patch_order_status_persists_transition_and_actor(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)

    response = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "ready"},
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "READY"
    db = session_factory()
    try:
        manager = db.scalar(select(User).where(User.email == "manager@example.test"))
        history = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id == uuid.UUID(order["id"])
            )
        ).all()
        assert manager is not None
        assert len(history) == 2
        transition = next(item for item in history if item.old_status == "DRAFT")
        assert transition.new_status == "READY"
        assert transition.changed_by == manager.id
    finally:
        db.close()


def test_patch_order_status_is_idempotent_without_duplicate_history(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)

    response = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "DRAFT"},
        headers=manager_headers,
    )

    assert response.status_code == 200
    db = session_factory()
    try:
        history = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id == uuid.UUID(order["id"])
            )
        ).all()
        assert len(history) == 1
    finally:
        db.close()


def test_patch_order_status_rejects_transition_reserved_for_plan_approval(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)

    response = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "PLANNED"},
        headers=manager_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "ORDER_STATUS_TRANSITION_NOT_ALLOWED",
        "message": "A transição de status do pedido não é permitida.",
        "details": [
            {
                "field": "status",
                "current_status": "DRAFT",
                "requested_status": "PLANNED",
            }
        ],
    }


def test_patch_order_rejects_edit_after_draft(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
) -> None:
    order = create_order(client, session_factory, manager_headers)
    status_response = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "READY"},
        headers=manager_headers,
    )
    assert status_response.status_code == 200

    response = client.patch(
        f"/api/v1/orders/{order['id']}",
        json={"priority": "HIGH"},
        headers=manager_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ORDER_EDIT_NOT_ALLOWED"
    assert response.json()["details"] == [
        {"field": "status", "current_status": "READY"}
    ]


def test_status_transition_rolls_back_when_history_persistence_fails(
    client: TestClient,
    session_factory: SessionFactory,
    manager_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = create_order(client, session_factory, manager_headers)

    def fail_history(
        _service: StatusHistoryService,
        _data: object,
    ) -> None:
        raise RuntimeError("simulated history persistence failure")

    monkeypatch.setattr(StatusHistoryService, "stage_status_change", fail_history)

    response = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "READY"},
        headers=manager_headers,
    )

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    db = session_factory()
    try:
        persisted_order = db.get(Order, uuid.UUID(order["id"]))
        history = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id == uuid.UUID(order["id"])
            )
        ).all()
        assert persisted_order is not None
        assert persisted_order.status == "DRAFT"
        assert len(history) == 1
    finally:
        db.close()


@pytest.mark.parametrize("role", ["ADMIN", "CHECKER"])
@pytest.mark.parametrize("route", ["collection", "detail"])
def test_read_only_roles_can_read_orders(
    client: TestClient,
    session_factory: SessionFactory,
    route: str,
    role: str,
) -> None:
    order = create_order_in_db(session_factory)
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role,
    )

    response = request_order_route(
        client,
        session_factory,
        "GET",
        route,
        order,
        authorization_headers(user),
    )

    assert response.status_code == 200


@pytest.mark.parametrize("role", ["ADMIN", "CHECKER"])
@pytest.mark.parametrize(
    ("method", "route"),
    [("POST", "collection"), ("PATCH", "detail"), ("PATCH", "status")],
)
def test_read_only_roles_cannot_manage_orders(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
    role: str,
) -> None:
    order = create_order_in_db(session_factory)
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role,
    )
    response = request_order_route(
        client,
        session_factory,
        method,
        route,
        order,
        authorization_headers(user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), ORDER_ROUTE_CASES)
def test_order_routes_require_authentication(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    order = create_order_in_db(session_factory)

    response = request_order_route(
        client,
        session_factory,
        method,
        route,
        order,
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize(("method", "route"), ORDER_ROUTE_CASES)
def test_order_routes_reject_driver(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    order = create_order_in_db(session_factory)
    driver = create_user_in_db(
        session_factory,
        "driver@example.test",
        "DRIVER",
    )

    response = request_order_route(
        client,
        session_factory,
        method,
        route,
        order,
        authorization_headers(driver),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), ORDER_ROUTE_CASES)
def test_order_routes_reject_inactive_manager(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    order = create_order_in_db(session_factory)
    manager = create_user_in_db(
        session_factory,
        "inactive-manager@example.test",
        "LOGISTICS_MANAGER",
        active=False,
    )

    response = request_order_route(
        client,
        session_factory,
        method,
        route,
        order,
        authorization_headers(manager),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_USER_INACTIVE"
