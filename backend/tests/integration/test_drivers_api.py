from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.drivers.models import Driver


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Driver.__table__])
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
        Base.metadata.drop_all(engine, tables=[Driver.__table__])


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


def test_create_driver_returns_created_resource(client: TestClient) -> None:
    response = client.post("/api/v1/drivers", json=make_driver_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["document"] == "00000000000"
    assert body["license_category"] == "D"
    assert body["active"] is True


def test_list_drivers_returns_created_items(client: TestClient) -> None:
    client.post("/api/v1/drivers", json=make_driver_payload())

    response = client.get("/api/v1/drivers")

    assert response.status_code == 200
    assert response.json()[0]["license_number"] == "CNH0001"


def test_get_driver_by_id_returns_created_item(client: TestClient) -> None:
    create_response = client.post("/api/v1/drivers", json=make_driver_payload())
    driver_id = create_response.json()["id"]

    response = client.get(f"/api/v1/drivers/{driver_id}")

    assert response.status_code == 200
    assert response.json()["document"] == "00000000000"


def test_patch_driver_updates_only_sent_fields(client: TestClient) -> None:
    create_response = client.post("/api/v1/drivers", json=make_driver_payload())
    driver_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/drivers/{driver_id}",
        json={"phone": "5511999999999", "license_category": "e", "active": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document"] == "00000000000"
    assert body["phone"] == "5511999999999"
    assert body["license_category"] == "E"
    assert body["active"] is False


def test_create_driver_returns_standard_error_for_duplicate_document(client: TestClient) -> None:
    client.post("/api/v1/drivers", json=make_driver_payload(document="00000000000", license_number="CNH0001"))

    response = client.post("/api/v1/drivers", json=make_driver_payload(document="00000000000", license_number="CNH0002"))

    assert response.status_code == 409
    assert response.json() == {
        "code": "DRIVER_DOCUMENT_ALREADY_EXISTS",
        "message": "Já existe um motorista cadastrado com este documento.",
        "details": [{"field": "document"}],
    }


def test_create_driver_returns_standard_error_for_duplicate_license_number(client: TestClient) -> None:
    client.post("/api/v1/drivers", json=make_driver_payload(document="00000000000", license_number="CNH0001"))

    response = client.post("/api/v1/drivers", json=make_driver_payload(document="00000000001", license_number="CNH0001"))

    assert response.status_code == 409
    assert response.json() == {
        "code": "DRIVER_LICENSE_NUMBER_ALREADY_EXISTS",
        "message": "Já existe um motorista cadastrado com esta CNH.",
        "details": [{"field": "license_number"}],
    }


def test_create_driver_rejects_invalid_license_category(client: TestClient) -> None:
    payload = make_driver_payload()
    payload["license_category"] = "ABCDEFGHI"

    response = client.post("/api/v1/drivers", json=payload)

    assert response.status_code == 422
