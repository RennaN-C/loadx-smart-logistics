from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.customers.models import Customer


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Customer.__table__])
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
        Base.metadata.drop_all(engine, tables=[Customer.__table__])


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


def test_create_customer_returns_created_resource(client: TestClient) -> None:
    response = client.post("/api/v1/customers", json=make_customer_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["document"] == "00000000000191"
    assert body["state"] == "SP"


def test_list_customers_returns_created_items(client: TestClient) -> None:
    client.post("/api/v1/customers", json=make_customer_payload())

    response = client.get("/api/v1/customers")

    assert response.status_code == 200
    assert response.json()[0]["document"] == "00000000000191"


def test_get_customer_by_id_returns_created_item(client: TestClient) -> None:
    create_response = client.post("/api/v1/customers", json=make_customer_payload())
    customer_id = create_response.json()["id"]

    response = client.get(f"/api/v1/customers/{customer_id}")

    assert response.status_code == 200
    assert response.json()["document"] == "00000000000191"


def test_patch_customer_updates_only_sent_fields(client: TestClient) -> None:
    create_response = client.post("/api/v1/customers", json=make_customer_payload())
    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"city": "Campinas", "state": "sp"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document"] == "00000000000191"
    assert body["city"] == "Campinas"
    assert body["state"] == "SP"


def test_patch_customer_rejects_null_required_field_with_standard_error(
    client: TestClient,
) -> None:
    create_response = client.post("/api/v1/customers", json=make_customer_payload())
    customer_id = create_response.json()["id"]

    response = client.patch(f"/api/v1/customers/{customer_id}", json={"name": None})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "name"


def test_patch_customer_accepts_null_nullable_field(client: TestClient) -> None:
    create_response = client.post("/api/v1/customers", json=make_customer_payload())
    customer_id = create_response.json()["id"]

    response = client.patch(f"/api/v1/customers/{customer_id}", json={"notes": None})

    assert response.status_code == 200
    assert response.json()["notes"] is None
    assert response.json()["document"] == "00000000000191"


def test_create_customer_returns_standard_error_for_duplicate_document(
    client: TestClient,
) -> None:
    client.post("/api/v1/customers", json=make_customer_payload("00000000000191"))

    response = client.post(
        "/api/v1/customers", json=make_customer_payload("00000000000191")
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "CUSTOMER_DOCUMENT_ALREADY_EXISTS",
        "message": "Já existe um cliente cadastrado com este documento.",
        "details": [{"field": "document"}],
    }


def test_create_customer_rejects_invalid_state(client: TestClient) -> None:
    payload = make_customer_payload()
    payload["state"] = "SPO"

    response = client.post("/api/v1/customers", json=payload)

    assert response.status_code == 422
