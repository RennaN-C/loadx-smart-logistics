from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService

SessionFactory = Callable[[], Session]


def create_user(
    session_factory: SessionFactory,
    email: str = "ADMIN@EXAMPLE.TEST",
    active: bool = True,
) -> User:
    db = session_factory()
    try:
        return UserService(db).create_user(
            UserCreate(
                name="Admin Local",
                email=email,
                password="senha-local",
                role="admin",
                active=active,
            )
        )
    finally:
        db.close()


def login_user(
    client: TestClient,
    email: str = "admin@example.test",
    password: str = "senha-local",
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def test_register_route_is_removed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin Local",
            "email": "admin@example.test",
            "password": "senha-local",
            "role": "admin",
        },
    )

    assert response.status_code == 404


def test_login_returns_bearer_token(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    create_user(session_factory)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ADMIN@EXAMPLE.TEST", "password": "senha-local"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_me_returns_authenticated_user(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    user = create_user(session_factory)
    token = login_user(client)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_login_returns_standard_error_for_invalid_password(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    create_user(session_factory)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "senha-errada"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "AUTH_INVALID_CREDENTIALS",
        "message": "E-mail ou senha inválidos.",
        "details": [],
    }


def test_login_returns_standard_error_for_inactive_user(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    create_user(session_factory, active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "senha-local"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "code": "AUTH_USER_INACTIVE",
        "message": "Usuário inativo.",
        "details": [],
    }


def test_me_returns_standard_error_for_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "code": "AUTH_INVALID_TOKEN",
        "message": "Token ausente ou inválido.",
        "details": [],
    }


def test_me_returns_standard_error_for_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "code": "AUTH_INVALID_TOKEN",
        "message": "Token ausente ou inválido.",
        "details": [],
    }


def test_me_returns_standard_error_for_invalid_authentication_scheme(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic invalid-credentials"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "code": "AUTH_INVALID_TOKEN",
        "message": "Token ausente ou inválido.",
        "details": [],
    }


def test_me_returns_standard_error_for_inactive_user(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    user = create_user(session_factory, active=False)
    token = create_access_token(str(user.id), {"role": "ADMIN"})

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "code": "AUTH_USER_INACTIVE",
        "message": "Usuário inativo.",
        "details": [],
    }
