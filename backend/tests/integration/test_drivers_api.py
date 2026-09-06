from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.drivers.models import Driver
from app.modules.drivers.schemas import DriverCreate
from app.modules.drivers.service import DriverService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers

SessionFactory = Callable[[], Session]
DRIVER_ROUTE_CASES = [
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
                password="senha-local-segura",
                role=role,
                active=active,
            )
        )
    finally:
        db.close()


def authorization_headers(
    session_factory: SessionFactory,
    user: User,
) -> dict[str, str]:
    return issue_session_headers(session_factory, user.id)


@pytest.fixture
def manager_headers(session_factory: SessionFactory) -> dict[str, str]:
    manager = create_user_in_db(
        session_factory,
        "manager@example.test",
        "LOGISTICS_MANAGER",
    )
    return authorization_headers(session_factory, manager)


def make_driver_payload(
    document: str = "00000000000",
    license_number: str = "CNH0001",
) -> dict[str, object]:
    return {
        "name": "Motorista Demonstracao",
        "document": document,
        "phone": "5500000000000",
        "license_number": license_number,
        "license_category": "d",
    }


def create_driver_in_db(session_factory: SessionFactory) -> Driver:
    db = session_factory()
    try:
        return DriverService(db).create_driver(
            DriverCreate.model_validate(make_driver_payload())
        )
    finally:
        db.close()


def request_driver_route(
    client: TestClient,
    method: str,
    route: str,
    driver: Driver,
    headers: dict[str, str] | None = None,
):
    path = "/api/v1/drivers"
    if route == "detail":
        path = f"{path}/{driver.id}"

    payload = None
    if method == "POST":
        payload = make_driver_payload("00000000001", "CNH0002")
    elif method == "PATCH":
        payload = {"phone": "5511999999999"}

    request_options: dict[str, object] = {}
    if payload is not None:
        request_options["json"] = payload
    if headers is not None:
        request_options["headers"] = headers
    return client.request(method, path, **request_options)


def test_create_driver_returns_created_resource(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/drivers",
        json=make_driver_payload(),
        headers=manager_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["document"] == "00000000000"
    assert body["license_category"] == "D"
    assert body["active"] is True


def test_list_drivers_returns_created_items(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/drivers",
        json=make_driver_payload(),
        headers=manager_headers,
    )

    response = client.get("/api/v1/drivers", headers=manager_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    driver = body["items"][0]
    assert set(driver) == {
        "id",
        "name",
        "license_category",
        "active",
        "created_at",
    }
    assert "document" not in driver
    assert "phone" not in driver
    assert "license_number" not in driver


def test_get_driver_by_id_returns_created_item(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/drivers",
        json=make_driver_payload(),
        headers=manager_headers,
    )
    driver_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/drivers/{driver_id}",
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["document"] == "00000000000"


def test_patch_driver_updates_only_sent_fields(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/drivers",
        json=make_driver_payload(),
        headers=manager_headers,
    )
    driver_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/drivers/{driver_id}",
        json={"phone": "5511999999999", "license_category": "e", "active": False},
        headers=manager_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document"] == "00000000000"
    assert body["phone"] == "5511999999999"
    assert body["license_category"] == "E"
    assert body["active"] is False


def test_patch_driver_rejects_null_required_field_with_standard_error(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/drivers",
        json=make_driver_payload(),
        headers=manager_headers,
    )
    driver_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/drivers/{driver_id}",
        json={"phone": None},
        headers=manager_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "phone"


def test_patch_driver_accepts_null_nullable_field(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/drivers",
        json=make_driver_payload(),
        headers=manager_headers,
    )
    driver_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/drivers/{driver_id}",
        json={"license_category": None},
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["license_category"] is None
    assert response.json()["document"] == "00000000000"


def test_create_driver_returns_standard_error_for_duplicate_document(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/drivers",
        json=make_driver_payload(document="00000000000", license_number="CNH0001"),
        headers=manager_headers,
    )

    response = client.post(
        "/api/v1/drivers",
        json=make_driver_payload(document="00000000000", license_number="CNH0002"),
        headers=manager_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "DRIVER_DOCUMENT_ALREADY_EXISTS",
        "message": "Já existe um motorista cadastrado com este documento.",
        "details": [{"field": "document"}],
    }


def test_create_driver_returns_standard_error_for_duplicate_license_number(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/drivers",
        json=make_driver_payload(document="00000000000", license_number="CNH0001"),
        headers=manager_headers,
    )

    response = client.post(
        "/api/v1/drivers",
        json=make_driver_payload(document="00000000001", license_number="CNH0001"),
        headers=manager_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "DRIVER_LICENSE_NUMBER_ALREADY_EXISTS",
        "message": "Já existe um motorista cadastrado com esta CNH.",
        "details": [{"field": "license_number"}],
    }


def test_create_driver_rejects_invalid_license_category(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    payload = make_driver_payload()
    payload["license_category"] = "ABCDEFGHI"

    response = client.post(
        "/api/v1/drivers",
        json=payload,
        headers=manager_headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("route", ["collection", "detail"])
def test_admin_can_read_drivers(
    client: TestClient,
    session_factory: SessionFactory,
    route: str,
) -> None:
    driver = create_driver_in_db(session_factory)
    admin = create_user_in_db(
        session_factory,
        "admin@example.test",
        "ADMIN",
    )

    response = request_driver_route(
        client,
        "GET",
        route,
        driver,
        authorization_headers(session_factory, admin),
    )

    assert response.status_code == 200


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_admin_cannot_manage_drivers(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
) -> None:
    driver = create_driver_in_db(session_factory)
    admin = create_user_in_db(
        session_factory,
        "admin@example.test",
        "ADMIN",
    )
    route = "collection" if method == "POST" else "detail"

    response = request_driver_route(
        client,
        method,
        route,
        driver,
        authorization_headers(session_factory, admin),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), DRIVER_ROUTE_CASES)
def test_driver_routes_require_authentication(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    driver = create_driver_in_db(session_factory)

    response = request_driver_route(client, method, route, driver)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize("role", ["CHECKER", "DRIVER"])
@pytest.mark.parametrize(("method", "route"), DRIVER_ROUTE_CASES)
def test_driver_routes_reject_roles_without_access(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
    role: str,
) -> None:
    driver = create_driver_in_db(session_factory)
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role,
    )

    response = request_driver_route(
        client,
        method,
        route,
        driver,
        authorization_headers(session_factory, user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), DRIVER_ROUTE_CASES)
def test_driver_routes_reject_inactive_manager(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    driver = create_driver_in_db(session_factory)
    manager = create_user_in_db(
        session_factory,
        "inactive-manager@example.test",
        "LOGISTICS_MANAGER",
        active=False,
    )

    response = request_driver_route(
        client,
        method,
        route,
        driver,
        authorization_headers(session_factory, manager),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_USER_INACTIVE"
