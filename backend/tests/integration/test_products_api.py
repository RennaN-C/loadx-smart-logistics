from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.modules.products.models import Product


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Product.__table__])
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
        Base.metadata.drop_all(engine, tables=[Product.__table__])


def make_product_payload(code: str = "CX-A") -> dict[str, object]:
    return {
        "code": code,
        "name": "Caixa A",
        "description": "Produto de demonstracao",
        "width_cm": 60,
        "height_cm": 50,
        "length_cm": 40,
        "weight_kg": "12.500",
        "fragile": False,
        "stackable": True,
        "rotation_allowed": True,
    }


def test_create_product_returns_created_resource(client: TestClient) -> None:
    response = client.post("/api/v1/products", json=make_product_payload("cx-a"))

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["code"] == "CX-A"
    assert Decimal(str(body["weight_kg"])) == Decimal("12.500")
    assert body["stackable"] is True


def test_list_products_returns_created_items(client: TestClient) -> None:
    client.post("/api/v1/products", json=make_product_payload("CX-A"))

    response = client.get("/api/v1/products")

    assert response.status_code == 200
    assert response.json()[0]["code"] == "CX-A"


def test_get_product_by_id_returns_created_item(client: TestClient) -> None:
    create_response = client.post("/api/v1/products", json=make_product_payload("CX-A"))
    product_id = create_response.json()["id"]

    response = client.get(f"/api/v1/products/{product_id}")

    assert response.status_code == 200
    assert response.json()["code"] == "CX-A"


def test_patch_product_updates_only_sent_fields(client: TestClient) -> None:
    create_response = client.post("/api/v1/products", json=make_product_payload("CX-A"))
    product_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/products/{product_id}",
        json={"name": "Caixa A reforcada", "fragile": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "CX-A"
    assert body["name"] == "Caixa A reforcada"
    assert body["fragile"] is True
    assert body["stackable"] is True


def test_patch_product_rejects_null_required_field_with_standard_error(
    client: TestClient,
) -> None:
    create_response = client.post("/api/v1/products", json=make_product_payload("CX-A"))
    product_id = create_response.json()["id"]

    response = client.patch(f"/api/v1/products/{product_id}", json={"weight_kg": None})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "weight_kg"


def test_patch_product_accepts_null_nullable_field(client: TestClient) -> None:
    create_response = client.post("/api/v1/products", json=make_product_payload("CX-A"))
    product_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/products/{product_id}", json={"description": None}
    )

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["code"] == "CX-A"


def test_create_product_returns_standard_error_for_duplicate_code(
    client: TestClient,
) -> None:
    client.post("/api/v1/products", json=make_product_payload("CX-A"))

    response = client.post("/api/v1/products", json=make_product_payload("cx-a"))

    assert response.status_code == 409
    assert response.json() == {
        "code": "PRODUCT_CODE_ALREADY_EXISTS",
        "message": "Já existe um produto cadastrado com este código.",
        "details": [{"field": "code"}],
    }


def test_create_product_rejects_invalid_dimensions(client: TestClient) -> None:
    payload = make_product_payload("CX-A")
    payload["width_cm"] = 0

    response = client.post("/api/v1/products", json=payload)

    assert response.status_code == 422


def test_create_product_rejects_invalid_weight(client: TestClient) -> None:
    payload = make_product_payload("CX-A")
    payload["weight_kg"] = "0"

    response = client.post("/api/v1/products", json=payload)

    assert response.status_code == 422
