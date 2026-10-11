import uuid
from unittest.mock import Mock

import pytest

from app.database.readiness import ReadinessCheckError, ReadinessFailureReason
from app.main import app
from app.modules.integration_health.schemas import IntegrationSignal
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_users_api import create_user_in_db


@pytest.fixture
def headers(session_factory):
    user = create_user_in_db(session_factory, "oc108-admin@example.test")
    return issue_session_headers(session_factory, user.id)


@pytest.fixture
def checker(monkeypatch):
    value = Mock(timeout_seconds=0.1)
    monkeypatch.setattr(app.state, "readiness_checker", value)
    return value


def test_admin_reads_current_statuses_and_correlation(client, headers, checker):
    response = client.get("/api/v1/integration-health", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "PARTIAL"
    assert uuid.UUID(body["correlation_id"])
    assert body["correlation_id"] == response.headers["X-Request-ID"]
    assert len(body["components"]) == 6
    assert set(body) == {"checked_at", "correlation_id", "overall_status", "components"}
    assert all(
        set(item) == {"component", "mode", "status", "configured", "reason_code"}
        for item in body["components"]
    )
    assert response.headers["cache-control"] == "no-store"
    checker.check.assert_called_once()


@pytest.mark.parametrize("role", ["LOGISTICS_MANAGER", "CHECKER", "DRIVER"])
def test_roles_cannot_access_or_execute_diagnostics(
    client, session_factory, checker, role
):
    user = create_user_in_db(session_factory, "role@example.test", role)
    response = client.get(
        "/api/v1/integration-health",
        headers=issue_session_headers(session_factory, user.id),
    )
    assert response.status_code == 403
    checker.check.assert_not_called()


def test_anonymous_cannot_execute_diagnostics(client, checker):
    assert client.get("/api/v1/integration-health").status_code == 401
    checker.check.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        ReadinessCheckError(ReadinessFailureReason.TIMEOUT),
        RuntimeError("postgresql://user:password@privatehost stack trace"),
    ],
)
def test_failure_is_partial_safe_and_http200(client, headers, checker, error):
    checker.check.side_effect = error
    response = client.get("/api/v1/integration-health", headers=headers)
    assert response.status_code == 200
    assert response.json()["overall_status"] == "DEGRADED"
    assert "password" not in response.text
    assert "privatehost" not in response.text
    assert "stack trace" not in response.text


class ApprovedSource:
    async def read_signal(self, *, timeout_seconds):
        return IntegrationSignal(
            mode="REAL", configured=True, approved=True, status="AVAILABLE"
        )


def test_real_provider_signal_requires_explicit_server_registration(
    client, headers, checker, monkeypatch
):
    monkeypatch.setattr(
        app.state, "integration_health_sources", {"ai": ApprovedSource()}
    )
    response = client.get("/api/v1/integration-health", headers=headers)
    ai = next(
        item for item in response.json()["components"] if item["component"] == "ai"
    )
    assert ai["mode"] == "REAL"
    assert ai["status"] == "AVAILABLE"
    assert "token" not in response.text
