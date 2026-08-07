from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate
from app.modules.customers.service import CustomerService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService

SessionFactory = Callable[[], Session]
CUSTOMER_ROUTE_CASES = [
    ("GET", "collection"),
    ("POST", "collection"),
    ("GET", "detail"),
    ("PATCH", "detail"),
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
                password="senha-local",
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


def make_customer_payload(document: str = "00000000000191") -> dict[str, object]:
    return {
        "name": "Cliente Demonstracao",
        "document": document,
        "phone": "5500000000000",
        "address": "Rua Exemplo, 100",
        "city": "Sao Paulo",
        "state": "sp",
        "notes": "Cliente ficticio para testes",
    }


def create_customer_in_db(session_factory: SessionFactory) -> Customer:
    db = session_factory()
    try:
        return CustomerService(db).create_customer(
            CustomerCreate.model_validate(make_customer_payload())
        )
    finally:
        db.close()


def request_customer_route(
    client: TestClient,
    method: str,
    route: str,
    customer: Customer,
    headers: dict[str, str] | None = None,
):
    path = "/api/v1/customers"
    if route == "detail":
        path = f"{path}/{customer.id}"

    payload = None
    if method == "POST":
        payload = make_customer_payload("00000000000272")
    elif method == "PATCH":
        payload = {"city": "Campinas"}

    request_options: dict[str, object] = {}
    if payload is not None:
        request_options["json"] = payload
    if headers is not None:
        request_options["headers"] = headers
    return client.request(method, path, **request_options)


def test_create_customer_returns_created_resource(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/customers",
        json=make_customer_payload(),
        headers=manager_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["document"] == "00000000000191"
    assert body["state"] == "SP"


def test_list_customers_returns_created_items(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/customers",
        json=make_customer_payload(),
        headers=manager_headers,
    )

    response = client.get("/api/v1/customers", headers=manager_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 1
    assert body["total_pages"] == 1
    customer = body["items"][0]
    assert set(customer) == {"id", "name", "city", "state", "created_at"}
    assert "document" not in customer
    assert "phone" not in customer
    assert "address" not in customer
    assert "notes" not in customer


def test_list_customers_returns_empty_page_metadata(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    response = client.get("/api/v1/customers", headers=manager_headers)

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "page_size": 20,
        "total": 0,
        "total_pages": 0,
    }


def test_get_customer_by_id_returns_created_item(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/customers",
        json=make_customer_payload(),
        headers=manager_headers,
    )
    customer_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["document"] == "00000000000191"


def test_patch_customer_updates_only_sent_fields(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/customers",
        json=make_customer_payload(),
        headers=manager_headers,
    )
    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"city": "Campinas", "state": "sp"},
        headers=manager_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document"] == "00000000000191"
    assert body["city"] == "Campinas"
    assert body["state"] == "SP"


def test_patch_customer_rejects_null_required_field_with_standard_error(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/customers",
        json=make_customer_payload(),
        headers=manager_headers,
    )
    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"name": None},
        headers=manager_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "name"


def test_patch_customer_accepts_null_nullable_field(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/customers",
        json=make_customer_payload(),
        headers=manager_headers,
    )
    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"notes": None},
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["notes"] is None
    assert response.json()["document"] == "00000000000191"


def test_create_customer_returns_standard_error_for_duplicate_document(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/customers",
        json=make_customer_payload("00000000000191"),
        headers=manager_headers,
    )

    response = client.post(
        "/api/v1/customers",
        json=make_customer_payload("00000000000191"),
        headers=manager_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "CUSTOMER_DOCUMENT_ALREADY_EXISTS",
        "message": "Já existe um cliente cadastrado com este documento.",
        "details": [{"field": "document"}],
    }


def test_create_customer_rejects_invalid_state(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    payload = make_customer_payload()
    payload["state"] = "SPO"

    response = client.post(
        "/api/v1/customers",
        json=payload,
        headers=manager_headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("route", ["collection", "detail"])
def test_admin_can_read_customers(
    client: TestClient,
    session_factory: SessionFactory,
    route: str,
) -> None:
    customer = create_customer_in_db(session_factory)
    admin = create_user_in_db(
        session_factory,
        "admin@example.test",
        "ADMIN",
    )

    response = request_customer_route(
        client,
        "GET",
        route,
        customer,
        authorization_headers(admin),
    )

    assert response.status_code == 200


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_admin_cannot_manage_customers(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
) -> None:
    customer = create_customer_in_db(session_factory)
    admin = create_user_in_db(
        session_factory,
        "admin@example.test",
        "ADMIN",
    )
    route = "collection" if method == "POST" else "detail"

    response = request_customer_route(
        client,
        method,
        route,
        customer,
        authorization_headers(admin),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), CUSTOMER_ROUTE_CASES)
def test_customer_routes_require_authentication(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    customer = create_customer_in_db(session_factory)

    response = request_customer_route(client, method, route, customer)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize("role", ["CHECKER", "DRIVER"])
@pytest.mark.parametrize(("method", "route"), CUSTOMER_ROUTE_CASES)
def test_customer_routes_reject_roles_without_access(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
    role: str,
) -> None:
    customer = create_customer_in_db(session_factory)
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role,
    )

    response = request_customer_route(
        client,
        method,
        route,
        customer,
        authorization_headers(user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), CUSTOMER_ROUTE_CASES)
def test_customer_routes_reject_inactive_manager(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    customer = create_customer_in_db(session_factory)
    manager = create_user_in_db(
        session_factory,
        "inactive-manager@example.test",
        "LOGISTICS_MANAGER",
        active=False,
    )

    response = request_customer_route(
        client,
        method,
        route,
        customer,
        authorization_headers(manager),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_USER_INACTIVE"
