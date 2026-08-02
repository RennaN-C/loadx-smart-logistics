import uuid
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


def make_user_payload(email: str = "ADMIN@EXAMPLE.TEST") -> dict[str, object]:
    return {
        "name": "Admin Local",
        "email": email,
        "password": "senha-local",
        "role": "admin",
    }


def test_create_user_returns_public_resource(client: TestClient) -> None:
    response = client.post("/api/v1/users", json=make_user_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["email"] == "admin@example.test"
    assert body["role"] == "ADMIN"
    assert body["active"] is True
    assert "password" not in body
    assert "password_hash" not in body


def test_list_users_returns_created_items(client: TestClient) -> None:
    create_response = client.post("/api/v1/users", json=make_user_payload())

    response = client.get("/api/v1/users")

    assert response.status_code == 200
    assert response.json()[0]["id"] == create_response.json()["id"]


def test_get_user_by_id_returns_created_item(client: TestClient) -> None:
    create_response = client.post("/api/v1/users", json=make_user_payload())
    user_id = create_response.json()["id"]

    response = client.get(f"/api/v1/users/{user_id}")

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.test"


def test_get_user_returns_standard_error_when_not_found(client: TestClient) -> None:
    response = client.get(f"/api/v1/users/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {
        "code": "USER_NOT_FOUND",
        "message": "Usuário não encontrado.",
        "details": [{"field": "id"}],
    }


def test_get_user_returns_standard_validation_error_for_invalid_uuid(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/users/invalid-uuid")

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "details"}
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert body["details"][0]["field"] == "user_id"


def test_patch_user_updates_only_sent_fields(client: TestClient) -> None:
    create_response = client.post("/api/v1/users", json=make_user_payload())
    user_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/users/{user_id}",
        json={
            "email": "MANAGER@EXAMPLE.TEST",
            "role": "logistics_manager",
            "active": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "manager@example.test"
    assert body["role"] == "LOGISTICS_MANAGER"
    assert body["active"] is False
    assert "password_hash" not in body


def test_patch_user_rejects_null_required_field_with_standard_error(
    client: TestClient,
) -> None:
    create_response = client.post("/api/v1/users", json=make_user_payload())
    user_id = create_response.json()["id"]

    response = client.patch(f"/api/v1/users/{user_id}", json={"name": None})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert body["details"][0]["field"] == "name"


def test_create_user_returns_standard_error_for_duplicate_email(
    client: TestClient,
) -> None:
    client.post("/api/v1/users", json=make_user_payload("admin@example.test"))

    response = client.post(
        "/api/v1/users", json=make_user_payload("ADMIN@EXAMPLE.TEST")
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "USER_EMAIL_ALREADY_EXISTS",
        "message": "Já existe um usuário cadastrado com este e-mail.",
        "details": [{"field": "email"}],
    }


def test_create_user_rejects_invalid_role(client: TestClient) -> None:
    payload = make_user_payload()
    payload["role"] = "invalid"

    response = client.post("/api/v1/users", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "details"}
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert body["details"][0]["field"] == "role"


def test_create_user_rejects_short_password(client: TestClient) -> None:
    payload = make_user_payload()
    payload["password"] = "curta"

    response = client.post("/api/v1/users", json=payload)

    assert response.status_code == 422
