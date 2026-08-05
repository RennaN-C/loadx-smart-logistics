from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.modules.trucks.models import Truck
from app.modules.trucks.schemas import TruckCreate
from app.modules.trucks.service import TruckService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService

SessionFactory = Callable[[], Session]
TRUCK_ROUTE_CASES = [
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


def make_truck_payload(plate: str = "ABC1D23") -> dict[str, object]:
    return {
        "plate": plate,
        "model": "Bau medio",
        "internal_width_cm": 240,
        "internal_height_cm": 260,
        "internal_length_cm": 600,
        "max_weight_kg": "8000.00",
    }


def create_truck_in_db(session_factory: SessionFactory) -> Truck:
    db = session_factory()
    try:
        return TruckService(db).create_truck(
            TruckCreate.model_validate(make_truck_payload())
        )
    finally:
        db.close()


def request_truck_route(
    client: TestClient,
    method: str,
    route: str,
    truck: Truck,
    headers: dict[str, str] | None = None,
):
    path = "/api/v1/trucks"
    if route == "detail":
        path = f"{path}/{truck.id}"

    payload = None
    if method == "POST":
        payload = make_truck_payload("DEF4G56")
    elif method == "PATCH":
        payload = {"model": "Bau pequeno"}

    request_options: dict[str, object] = {}
    if payload is not None:
        request_options["json"] = payload
    if headers is not None:
        request_options["headers"] = headers
    return client.request(method, path, **request_options)


def test_create_truck_returns_created_resource(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/trucks",
        json=make_truck_payload("abc1d23"),
        headers=manager_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["plate"] == "ABC1D23"
    assert body["active"] is True


def test_list_trucks_returns_created_items(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/trucks",
        json=make_truck_payload("ABC1D23"),
        headers=manager_headers,
    )

    response = client.get("/api/v1/trucks", headers=manager_headers)

    assert response.status_code == 200
    assert response.json()[0]["plate"] == "ABC1D23"


def test_get_truck_by_id_returns_created_item(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/trucks",
        json=make_truck_payload("ABC1D23"),
        headers=manager_headers,
    )
    truck_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/trucks/{truck_id}",
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["plate"] == "ABC1D23"


def test_patch_truck_updates_only_sent_fields(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/trucks",
        json=make_truck_payload("ABC1D23"),
        headers=manager_headers,
    )
    truck_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/trucks/{truck_id}",
        json={"model": "Bau pequeno", "active": False},
        headers=manager_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["plate"] == "ABC1D23"
    assert body["model"] == "Bau pequeno"
    assert body["active"] is False


def test_patch_truck_rejects_null_required_field_with_standard_error(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/trucks",
        json=make_truck_payload("ABC1D23"),
        headers=manager_headers,
    )
    truck_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/trucks/{truck_id}",
        json={"max_weight_kg": None},
        headers=manager_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "max_weight_kg"


def test_create_truck_returns_standard_error_for_duplicate_plate(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/trucks",
        json=make_truck_payload("ABC1D23"),
        headers=manager_headers,
    )

    response = client.post(
        "/api/v1/trucks",
        json=make_truck_payload("abc1d23"),
        headers=manager_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "TRUCK_PLATE_ALREADY_EXISTS",
        "message": "Já existe um caminhão cadastrado com esta placa.",
        "details": [{"field": "plate"}],
    }


def test_create_truck_rejects_invalid_dimensions(
    client: TestClient,
    manager_headers: dict[str, str],
) -> None:
    payload = make_truck_payload("ABC1D23")
    payload["internal_width_cm"] = 0

    response = client.post(
        "/api/v1/trucks",
        json=payload,
        headers=manager_headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("role", ["ADMIN", "CHECKER"])
@pytest.mark.parametrize("route", ["collection", "detail"])
def test_read_only_roles_can_read_trucks(
    client: TestClient,
    session_factory: SessionFactory,
    route: str,
    role: str,
) -> None:
    truck = create_truck_in_db(session_factory)
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role,
    )

    response = request_truck_route(
        client,
        "GET",
        route,
        truck,
        authorization_headers(user),
    )

    assert response.status_code == 200


@pytest.mark.parametrize("role", ["ADMIN", "CHECKER"])
@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_read_only_roles_cannot_manage_trucks(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    role: str,
) -> None:
    truck = create_truck_in_db(session_factory)
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role,
    )
    route = "collection" if method == "POST" else "detail"

    response = request_truck_route(
        client,
        method,
        route,
        truck,
        authorization_headers(user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), TRUCK_ROUTE_CASES)
def test_truck_routes_require_authentication(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    truck = create_truck_in_db(session_factory)

    response = request_truck_route(client, method, route, truck)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize(("method", "route"), TRUCK_ROUTE_CASES)
def test_truck_routes_reject_driver(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    truck = create_truck_in_db(session_factory)
    driver = create_user_in_db(
        session_factory,
        "driver@example.test",
        "DRIVER",
    )

    response = request_truck_route(
        client,
        method,
        route,
        truck,
        authorization_headers(driver),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize(("method", "route"), TRUCK_ROUTE_CASES)
def test_truck_routes_reject_inactive_manager(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    route: str,
) -> None:
    truck = create_truck_in_db(session_factory)
    manager = create_user_in_db(
        session_factory,
        "inactive-manager@example.test",
        "LOGISTICS_MANAGER",
        active=False,
    )

    response = request_truck_route(
        client,
        method,
        route,
        truck,
        authorization_headers(manager),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_USER_INACTIVE"
