from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.trucks.models import Truck


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Truck.__table__])
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
        Base.metadata.drop_all(engine, tables=[Truck.__table__])


def make_truck_payload(plate: str = "ABC1D23") -> dict[str, object]:
    return {
        "plate": plate,
        "model": "Bau medio",
        "internal_width_cm": 240,
        "internal_height_cm": 260,
        "internal_length_cm": 600,
        "max_weight_kg": "8000.00",
    }


def test_create_truck_returns_created_resource(client: TestClient) -> None:
    response = client.post("/api/v1/trucks", json=make_truck_payload("abc1d23"))

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["plate"] == "ABC1D23"
    assert body["active"] is True


def test_list_trucks_returns_created_items(client: TestClient) -> None:
    client.post("/api/v1/trucks", json=make_truck_payload("ABC1D23"))

    response = client.get("/api/v1/trucks")

    assert response.status_code == 200
    assert response.json()[0]["plate"] == "ABC1D23"


def test_get_truck_by_id_returns_created_item(client: TestClient) -> None:
    create_response = client.post("/api/v1/trucks", json=make_truck_payload("ABC1D23"))
    truck_id = create_response.json()["id"]

    response = client.get(f"/api/v1/trucks/{truck_id}")

    assert response.status_code == 200
    assert response.json()["plate"] == "ABC1D23"


def test_patch_truck_updates_only_sent_fields(client: TestClient) -> None:
    create_response = client.post("/api/v1/trucks", json=make_truck_payload("ABC1D23"))
    truck_id = create_response.json()["id"]

    response = client.patch(f"/api/v1/trucks/{truck_id}", json={"model": "Bau pequeno", "active": False})

    assert response.status_code == 200
    body = response.json()
    assert body["plate"] == "ABC1D23"
    assert body["model"] == "Bau pequeno"
    assert body["active"] is False


def test_create_truck_returns_standard_error_for_duplicate_plate(client: TestClient) -> None:
    client.post("/api/v1/trucks", json=make_truck_payload("ABC1D23"))

    response = client.post("/api/v1/trucks", json=make_truck_payload("abc1d23"))

    assert response.status_code == 409
    assert response.json() == {
        "code": "TRUCK_PLATE_ALREADY_EXISTS",
        "message": "Já existe um caminhão cadastrado com esta placa.",
        "details": [{"field": "plate"}],
    }


def test_create_truck_rejects_invalid_dimensions(client: TestClient) -> None:
    payload = make_truck_payload("ABC1D23")
    payload["internal_width_cm"] = 0

    response = client.post("/api/v1/trucks", json=payload)

    assert response.status_code == 422
