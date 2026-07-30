from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.users.models import User


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine, tables=[User.__table__])


def make_register_payload(email: str = "ADMIN@EXAMPLE.TEST", active: bool = True) -> dict[str, object]:
    return {
        "name": "Admin Local",
        "email": email,
        "password": "senha-local",
        "role": "admin",
        "active": active,
    }


def register_user(client: TestClient) -> dict[str, object]:
    response = client.post("/api/v1/auth/register", json=make_register_payload())
    assert response.status_code == 201
    return response.json()


def login_user(client: TestClient, email: str = "admin@example.test", password: str = "senha-local") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def test_register_returns_public_user(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=make_register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["email"] == "admin@example.test"
    assert body["role"] == "ADMIN"
    assert "password_hash" not in body


def test_register_returns_standard_error_for_duplicate_email(client: TestClient) -> None:
    register_user(client)

    response = client.post("/api/v1/auth/register", json=make_register_payload("ADMIN@EXAMPLE.TEST"))

    assert response.status_code == 409
    assert response.json() == {
        "code": "USER_EMAIL_ALREADY_EXISTS",
        "message": "Já existe um usuário cadastrado com este e-mail.",
        "details": [{"field": "email"}],
    }


def test_login_returns_bearer_token(client: TestClient) -> None:
    register_user(client)

    response = client.post("/api/v1/auth/login", json={"email": "ADMIN@EXAMPLE.TEST", "password": "senha-local"})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_me_returns_authenticated_user(client: TestClient) -> None:
    user = register_user(client)
    token = login_user(client)

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]


def test_login_returns_standard_error_for_invalid_password(client: TestClient) -> None:
    register_user(client)

    response = client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": "senha-errada"})

    assert response.status_code == 401
    assert response.json() == {
        "code": "AUTH_INVALID_CREDENTIALS",
        "message": "E-mail ou senha inválidos.",
        "details": [],
    }


def test_login_returns_standard_error_for_inactive_user(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=make_register_payload(active=False))
    assert response.status_code == 201

    response = client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": "senha-local"})

    assert response.status_code == 403
    assert response.json() == {
        "code": "AUTH_USER_INACTIVE",
        "message": "Usuário inativo.",
        "details": [],
    }


def test_me_returns_standard_error_for_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "code": "AUTH_INVALID_TOKEN",
        "message": "Token ausente ou inválido.",
        "details": [],
    }


def test_me_returns_standard_error_for_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
    assert response.json() == {
        "code": "AUTH_INVALID_TOKEN",
        "message": "Token ausente ou inválido.",
        "details": [],
    }
