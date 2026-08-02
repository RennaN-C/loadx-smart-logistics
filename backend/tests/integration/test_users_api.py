import uuid
from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService

SessionFactory = Callable[[], Session]


@pytest.fixture
def session_factory() -> Generator[SessionFactory, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield testing_session_local
    finally:
        Base.metadata.drop_all(engine, tables=[User.__table__])


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


def create_user_in_db(
    session_factory: SessionFactory,
    email: str,
    role: str = "ADMIN",
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
def admin_user(session_factory: SessionFactory) -> User:
    return create_user_in_db(session_factory, "admin@example.test")


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    return authorization_headers(admin_user)


def make_user_payload(
    email: str = "USER@EXAMPLE.TEST",
    role: str = "checker",
) -> dict[str, object]:
    return {
        "name": "Usuário Local",
        "email": email,
        "password": "senha-local",
        "role": role,
    }


def test_create_user_returns_public_resource(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/users",
        json=make_user_payload(),
        headers=admin_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["email"] == "user@example.test"
    assert body["role"] == "CHECKER"
    assert body["active"] is True
    assert "password" not in body
    assert "password_hash" not in body


def test_list_users_returns_created_items(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/users",
        json=make_user_payload(),
        headers=admin_headers,
    )

    response = client.get("/api/v1/users", headers=admin_headers)

    assert response.status_code == 200
    created_id = create_response.json()["id"]
    assert any(user["id"] == created_id for user in response.json())


def test_get_user_by_id_returns_created_item(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/users",
        json=make_user_payload(),
        headers=admin_headers,
    )
    user_id = create_response.json()["id"]

    response = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.test"


def test_get_user_returns_standard_error_when_not_found(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.get(
        f"/api/v1/users/{uuid.uuid4()}",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "code": "USER_NOT_FOUND",
        "message": "Usuário não encontrado.",
        "details": [{"field": "id"}],
    }


def test_get_user_returns_standard_validation_error_for_invalid_uuid(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/users/invalid-uuid",
        headers=admin_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "details"}
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert body["details"][0]["field"] == "user_id"


def test_patch_user_updates_only_sent_fields(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/users",
        json=make_user_payload(),
        headers=admin_headers,
    )
    user_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/users/{user_id}",
        json={
            "email": "MANAGER@EXAMPLE.TEST",
            "role": "logistics_manager",
            "active": False,
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "manager@example.test"
    assert body["role"] == "LOGISTICS_MANAGER"
    assert body["active"] is False
    assert "password_hash" not in body


def test_patch_user_rejects_null_required_field_with_standard_error(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/users",
        json=make_user_payload(),
        headers=admin_headers,
    )
    user_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/users/{user_id}",
        json={"name": None},
        headers=admin_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert body["details"][0]["field"] == "name"


def test_create_user_returns_standard_error_for_duplicate_email(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/users",
        json=make_user_payload("duplicate@example.test"),
        headers=admin_headers,
    )

    response = client.post(
        "/api/v1/users",
        json=make_user_payload("DUPLICATE@EXAMPLE.TEST"),
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "USER_EMAIL_ALREADY_EXISTS",
        "message": "Já existe um usuário cadastrado com este e-mail.",
        "details": [{"field": "email"}],
    }


def test_create_user_rejects_invalid_role(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    payload = make_user_payload()
    payload["role"] = "invalid"

    response = client.post(
        "/api/v1/users",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "details"}
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert body["details"][0]["field"] == "role"


def test_create_user_rejects_short_password(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    payload = make_user_payload()
    payload["password"] = "curta"

    response = client.post(
        "/api/v1/users",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/v1/users", None),
        ("POST", "/api/v1/users", make_user_payload()),
        ("GET", f"/api/v1/users/{uuid.uuid4()}", None),
        ("PATCH", f"/api/v1/users/{uuid.uuid4()}", {"name": "Novo nome"}),
    ],
)
def test_users_routes_require_authentication(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/v1/users", None),
        ("POST", "/api/v1/users", make_user_payload()),
        ("GET", f"/api/v1/users/{uuid.uuid4()}", None),
        ("PATCH", f"/api/v1/users/{uuid.uuid4()}", {"name": "Novo nome"}),
    ],
)
def test_users_routes_reject_non_admin_user(
    client: TestClient,
    session_factory: SessionFactory,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    user = create_user_in_db(
        session_factory,
        "checker@example.test",
        role="CHECKER",
    )

    response = client.request(
        method,
        path,
        json=payload,
        headers=authorization_headers(user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


@pytest.mark.parametrize("role", ["CHECKER", "DRIVER", "LOGISTICS_MANAGER"])
def test_list_users_rejects_each_non_admin_role(
    client: TestClient,
    session_factory: SessionFactory,
    role: str,
) -> None:
    user = create_user_in_db(
        session_factory,
        f"{role.lower()}@example.test",
        role=role,
    )

    response = client.get(
        "/api/v1/users",
        headers=authorization_headers(user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


def test_list_users_rejects_inactive_admin(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    user = create_user_in_db(
        session_factory,
        "inactive-admin@example.test",
        active=False,
    )

    response = client.get(
        "/api/v1/users",
        headers=authorization_headers(user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_USER_INACTIVE"


@pytest.mark.parametrize(
    "payload",
    [{"active": False}, {"role": "checker"}],
)
def test_patch_rejects_removing_last_active_admin(
    client: TestClient,
    admin_user: User,
    admin_headers: dict[str, str],
    payload: dict[str, object],
) -> None:
    response = client.patch(
        f"/api/v1/users/{admin_user.id}",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "USER_LAST_ACTIVE_ADMIN_REQUIRED",
        "message": "O último administrador ativo não pode ser desativado ou rebaixado.",
        "details": [{"field": "role"}, {"field": "active"}],
    }


def test_patch_allows_removing_admin_when_another_active_admin_exists(
    client: TestClient,
    session_factory: SessionFactory,
    admin_user: User,
    admin_headers: dict[str, str],
) -> None:
    create_user_in_db(session_factory, "second-admin@example.test")

    response = client.patch(
        f"/api/v1/users/{admin_user.id}",
        json={"role": "checker", "active": False},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["role"] == "CHECKER"
    assert response.json()["active"] is False
