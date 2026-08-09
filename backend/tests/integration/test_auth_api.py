from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.auth.dependencies import CSRF_HEADER_NAME
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers

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
                password="senha-local-segura",
                role="admin",
                active=active,
            )
        )
    finally:
        db.close()


def login_user(
    client: TestClient,
    email: str = "admin@example.test",
    password: str = "senha-local-segura",
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.headers[CSRF_HEADER_NAME]


def test_register_route_is_removed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin Local",
            "email": "admin@example.test",
            "password": "senha-local-segura",
            "role": "admin",
        },
    )

    assert response.status_code == 404


def test_login_returns_user_secure_local_cookie_and_csrf_header(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    user = create_user(session_factory)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ADMIN@EXAMPLE.TEST", "password": "senha-local-segura"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.headers[CSRF_HEADER_NAME]
    assert client.cookies.get(settings.session_cookie_name)
    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    assert "Domain=" not in set_cookie
    assert "Secure" not in set_cookie
    assert "access_token" not in response.json()


def test_me_restores_user_and_csrf_from_session_cookie(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    user = create_user(session_factory)
    login_csrf = login_user(client)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.headers[CSRF_HEADER_NAME] == login_csrf


def test_logout_requires_csrf_revokes_session_and_clears_cookie(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    create_user(session_factory)
    csrf_token = login_user(client)

    response = client.post(
        "/api/v1/auth/logout",
        headers={CSRF_HEADER_NAME: csrf_token},
    )

    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_rejects_missing_csrf_token(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    create_user(session_factory)
    login_user(client)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_CSRF_INVALID"


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


def test_login_returns_same_error_for_inactive_user(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    create_user(session_factory, active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "senha-local-segura"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


def test_login_rate_limit_is_generic_and_includes_retry_after(
    client: TestClient,
) -> None:
    payload = {"email": "unknown@example.test", "password": "senha-errada"}
    for _ in range(5):
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 429
    assert response.json()["code"] == "AUTH_RATE_LIMITED"
    assert response.headers["retry-after"] == "60"


def test_unsafe_request_rejects_unapproved_origin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://attacker.example"},
        json={"email": "admin@example.test", "password": "senha-local-segura"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_ORIGIN_FORBIDDEN"


def test_me_returns_standard_error_for_missing_session(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert "www-authenticate" not in response.headers
    assert response.json() == {
        "code": "AUTH_INVALID_TOKEN",
        "message": "Sessão ausente ou inválida.",
        "details": [],
    }


def test_me_returns_standard_error_for_invalid_session(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Cookie": f"{settings.session_cookie_name}=invalid-session"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


def test_me_returns_standard_error_for_inactive_user(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    user = create_user(session_factory, active=False)

    response = client.get(
        "/api/v1/auth/me",
        headers=issue_session_headers(session_factory, user.id),
    )

    assert response.status_code == 403
    assert response.json() == {
        "code": "AUTH_USER_INACTIVE",
        "message": "Usuário inativo.",
        "details": [],
    }
