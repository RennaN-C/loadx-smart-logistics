import logging

import pytest
from fastapi.testclient import TestClient

from app.database.readiness import ReadinessCheckError, ReadinessFailureReason
from app.main import app, get_readiness_checker


class PassingReadinessChecker:
    def check(self) -> None:
        return None


class FailingReadinessChecker:
    def check(self) -> None:
        raise ReadinessCheckError(ReadinessFailureReason.DATABASE_UNAVAILABLE)


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_returns_generic_success() -> None:
    app.dependency_overrides[get_readiness_checker] = PassingReadinessChecker
    try:
        with TestClient(app) as client:
            response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "loadx-api"}


def test_readiness_failure_does_not_expose_internal_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app.dependency_overrides[get_readiness_checker] = FailingReadinessChecker
    try:
        with caplog.at_level(logging.WARNING), TestClient(app) as client:
            response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "code": "SERVICE_NOT_READY",
        "message": "O serviço não está pronto.",
        "details": [],
    }
    assert "DATABASE_UNAVAILABLE" in caplog.text
