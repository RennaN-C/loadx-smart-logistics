from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.database.readiness import DatabaseReadinessChecker
from app.main import app, get_readiness_checker


def _database_url(engine: Engine) -> str:
    return engine.url.render_as_string(hide_password=False)


def test_readiness_accepts_available_database_at_alembic_head(
    client: TestClient,
) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "loadx-api"}


def test_readiness_rejects_unavailable_database(client: TestClient) -> None:
    checker = DatabaseReadinessChecker(
        "postgresql+psycopg://loadx_test:local@127.0.0.1:1/loadx_test",
        timeout_seconds=1,
    )
    app.dependency_overrides[get_readiness_checker] = lambda: checker

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "code": "SERVICE_NOT_READY",
        "message": "O serviço não está pronto.",
        "details": [],
    }


def test_readiness_rejects_database_outside_alembic_head(
    client: TestClient,
    postgres_engine: Engine,
) -> None:
    checker = DatabaseReadinessChecker(
        _database_url(postgres_engine),
        expected_heads=frozenset({"revision-not-deployed"}),
    )
    app.dependency_overrides[get_readiness_checker] = lambda: checker

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "code": "SERVICE_NOT_READY",
        "message": "O serviço não está pronto.",
        "details": [],
    }

