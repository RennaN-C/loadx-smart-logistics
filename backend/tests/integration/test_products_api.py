from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate
from app.modules.products.service import ProductService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService

SessionFactory = Callable[[], Session]
PRODUCT_ROUTE_CASES = [
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


def make_product_payload(code: str = "CX-A") -> dict[str, object]:
    return {
        "code": code,
        "name": "Caixa A",
        "description": "Produto de demonstracao",
        "width_cm": 60,
        "height_cm": 50,
        "length_cm": 40,
        "weight_kg": 12.500,
        "fragile": False,
        "stackable": True,
        "rotation_allowed": True,
    }


def create_product_in_db(session_factory: SessionFactory) -> Product:
    db = session_factory()
    try:
        return ProductService(db).create_product(
            ProductCreate.model_validate(make_product_payload())
        )
    finally:
        db.close()


def request_product_route(
    client: TestClient,
    method: str,
    route: str,
    product: Product,
    headers: dict[str, str] | None = None,
):
    path = "/api/v1/products"
    if route == "detail":
        path = f"{path}/{product.id}"

    payload = None
    if method == "POST":
        payload = make_product_payload("CX-B")
    elif method == "PATCH":
        payload = {"name": "Caixa reforcada"}

    request_options: dict[str, object] = {}
    if payload is not None:
        request_options["json"] = payload
    if headers is not None:
        request_options["headers"] = headers
    return client.request(method, path, **request_options)


def test_create_product_returns_created_resource(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/products",
        json=make_product_payload("cx-a"),
        headers=manager_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["code"] == "CX-A"
    assert body["weight_kg"] == 12.5
    assert isinstance(body["weight_kg"], float)
    assert body["stackable"] is True


def test_create_product_rejects_decimal_string(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    payload = make_product_payload()
    payload["weight_kg"] = "12.500"

    response = client.post(
        "/api/v1/products",
        json=payload,
        headers=manager_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["details"][0]["field"] == "weight_kg"


def test_list_products_returns_created_items(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/products",
        json=make_product_payload("CX-A"),
        headers=manager_headers,
    )

    response = client.get("/api/v1/products", headers=manager_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["code"] == "CX-A"
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 1
    assert body["total_pages"] == 1


def test_get_product_by_id_returns_created_item(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/products",
        json=make_product_payload("CX-A"),
        headers=manager_headers,
    )
    product_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/products/{product_id}",
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["code"] == "CX-A"


def test_patch_product_updates_only_sent_fields(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/products",
        json=make_product_payload("CX-A"),
        headers=manager_headers,
    )
    product_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/products/{product_id}",
        json={"name": "Caixa A reforcada", "fragile": True},
        headers=manager_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "CX-A"
    assert body["name"] == "Caixa A reforcada"
    assert body["fragile"] is True
    assert body["stackable"] is True


def test_patch_product_rejects_null_required_field_with_standard_error(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/products",
        json=make_product_payload("CX-A"),
        headers=manager_headers,
    )
    product_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/products/{product_id}",
        json={"weight_kg": None},
        headers=manager_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "weight_kg"


def test_patch_product_accepts_null_nullable_field(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/products",
        json=make_product_payload("CX-A"),
        headers=manager_headers,
    )
    product_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/products/{product_id}",
        json={"description": None},
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["code"] == "CX-A"


def test_create_product_returns_standard_error_for_duplicate_code(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/products",
        json=make_product_payload("CX-A"),
        headers=manager_headers,
    )

    response = client.post(
        "/api/v1/products",
        json=make_product_payload("cx-a"),
        headers=manager_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "PRODUCT_CODE_ALREADY_EXISTS",
        "message": "Já existe um produto cadastrado com este código.",
        "details": [{"field": "code"}],
    }


def test_create_product_rejects_invalid_dimensions(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    payload = make_product_payload("CX-A")
    payload["width_cm"] = 0

    response = client.post(
        "/api/v1/products",
        json=payload,
        headers=manager_headers,
    )

    assert response.status_code == 422


def test_create_product_rejects_invalid_weight(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    payload = make_product_payload("CX-A")
    payload["weight_kg"] = "0"

    response = client.post(
        "/api/v1/products",
        json=payload,
        headers=manager_headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("role", ["ADMIN", "CHECKER"])
@pytest.mark.parametrize("route", ["collection", "detail"])
def test_read_only_roles_can_read_products(
    client: TestClient,
    session_factory: SessionFactory,
    route: str,
    role: str,
) -> None:
    product = create_product_in_db(session_factory)
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role,
    )

    response = request_product_route(
        client,
        "GET",
        route,
        product,
        authorization_headers(user),
    )

    assert response.status_code == 200


@pytest.mark.parametrize("role", ["ADMIN", "CHECKER"])
@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_read_only_roles_cannot_manage_products(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    role: str,
) -> None:
    product = create_product_in_db(session_factory)
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role,
    )
    route = "collection" if method == "POST" else "detail"

    response = request_product_route(
        client,
        method,
        route,
        product,
        authorization_headers(user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), PRODUCT_ROUTE_CASES)
def test_product_routes_require_authentication(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    product = create_product_in_db(session_factory)

    response = request_product_route(client, method, route, product)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize(("method", "route"), PRODUCT_ROUTE_CASES)
def test_product_routes_reject_driver(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    product = create_product_in_db(session_factory)
    driver = create_user_in_db(
        session_factory,
        "driver@example.test",
        "DRIVER",
    )

    response = request_product_route(
        client,
        method,
        route,
        product,
        authorization_headers(driver),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), PRODUCT_ROUTE_CASES)
def test_product_routes_reject_inactive_manager(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    product = create_product_in_db(session_factory)
    manager = create_user_in_db(
        session_factory,
        "inactive-manager@example.test",
        "LOGISTICS_MANAGER",
        active=False,
    )

    response = request_product_route(
        client,
        method,
        route,
        product,
        authorization_headers(manager),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_USER_INACTIVE"
