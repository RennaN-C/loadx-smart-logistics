import json
import logging
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.core.observability import (
    OperationalEvent,
    SafeServerErrorFilter,
    configure_observability,
    emit_operational_event,
    request_id_context,
)
from app.database.readiness import ReadinessCheckError, ReadinessFailureReason
from app.main import create_app, get_readiness_checker
from app.modules.notifications.service import OperationalNotificationService


def _events(caplog):
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "loadx.operations"
    ]


def test_request_context_redacts_path_query_headers_and_resets(caplog):
    app = create_app()

    @app.get("/diagnostic/{value}")
    def diagnostic(value: str):
        return {"ok": True}

    with (
        caplog.at_level(logging.INFO, logger="loadx.operations"),
        TestClient(app) as client,
    ):
        first = client.get(
            "/diagnostic/private-email?token=query-secret",
            headers={
                "Authorization": "Bearer token-secret",
                "X-Request-ID": "injected-secret",
            },
        )
        second = client.get("/private-unknown-path?password=another-secret")
    completed = [
        event for event in _events(caplog) if event["event"] == "HTTP_REQUEST_COMPLETED"
    ]
    assert len(completed) == 2
    assert completed[0]["route"] == "/diagnostic/{value}"
    assert completed[1]["route"] == "__unmatched__"
    assert completed[0]["status_code"] == 200
    assert completed[1]["status_code"] == 404
    assert completed[0]["duration_ms"] >= 0
    assert completed[0]["request_id"] == first.headers["x-request-id"]
    assert uuid.UUID(first.headers["x-request-id"]) != uuid.UUID(
        second.headers["x-request-id"]
    )
    assert request_id_context.get() is None
    for marker in (
        "private-email",
        "query-secret",
        "token-secret",
        "injected-secret",
        "private-unknown-path",
        "another-secret",
    ):
        assert marker not in json.dumps(_events(caplog))


def test_critical_exception_has_correlated_safe_events(caplog):
    app = create_app()

    @app.get("/failure/{value}")
    def failure(value: str):
        raise RuntimeError("secret-password-from-provider")

    with (
        caplog.at_level(logging.INFO, logger="loadx.operations"),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get("/failure/private-document?token=secret-query")
    assert response.status_code == 500
    events = [
        event for event in _events(caplog) if event["event"].startswith("HTTP_REQUEST_")
    ]
    assert {event["event"] for event in events} == {
        "HTTP_REQUEST_COMPLETED",
        "HTTP_REQUEST_FAILED",
    }
    assert all(event["status_code"] == 500 and event["alert"] for event in events)
    assert all(
        event["request_id"] == response.headers["x-request-id"] for event in events
    )
    assert all(event["route"] == "/failure/{value}" for event in events)
    assert "private-document" not in json.dumps(events)
    assert "secret-password" not in caplog.text
    assert "secret-query" not in json.dumps(events)


def test_readiness_failure_and_lifecycle_are_observable(caplog):
    class FailingChecker:
        def check(self):
            raise ReadinessCheckError(ReadinessFailureReason.DATABASE_UNAVAILABLE)

    app = create_app()
    app.dependency_overrides[get_readiness_checker] = FailingChecker
    with (
        caplog.at_level(logging.INFO, logger="loadx.operations"),
        TestClient(app) as client,
    ):
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
    assert response.status_code == 503
    events = _events(caplog)
    assert {"APP_STARTED", "APP_STOPPED", "READINESS_FAILED"} <= {
        event["event"] for event in events
    }
    failure = next(event for event in events if event["event"] == "READINESS_FAILED")
    assert failure["reason"] == "DATABASE_UNAVAILABLE"
    assert failure["alert"]
    assert failure["request_id"] == response.headers["x-request-id"]
    assert "DATABASE_UNAVAILABLE" not in response.text


def test_notification_failure_never_logs_provider_payload(caplog):
    class FailingProvider:
        def send_response(self, message):
            raise RuntimeError("phone=private-phone token=secret-provider")

    service = OperationalNotificationService(FailingProvider())
    with caplog.at_level(logging.WARNING, logger="loadx.operations"):
        assert not service.notify_trip_started(
            recipient_phone="private-phone", trip_id=uuid.uuid4()
        )
    failure = _events(caplog)[0]
    assert failure["event"] == "NOTIFICATION_FAILED"
    assert failure["reason"] == "DELIVERY_FAILED"
    assert failure["exception_type"] == "RuntimeError"
    assert "private-phone" not in caplog.text
    assert "secret-provider" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_server_filter_removes_exception_and_cached_traceback():
    try:
        raise RuntimeError("secret-provider-message")
    except RuntimeError:
        record = logging.LogRecord(
            "uvicorn.error",
            logging.ERROR,
            __file__,
            1,
            "Error %s",
            ("secret-argument",),
            sys.exc_info(),
        )
    record.exc_text = "secret-cached-traceback"
    assert SafeServerErrorFilter().filter(record)
    rendered = logging.Formatter().format(record)
    assert "secret" not in rendered
    assert record.exc_info is None


@pytest.mark.parametrize("environment", ["local", "production"])
def test_operational_configuration_by_environment(environment, monkeypatch):
    monkeypatch.setenv("OPERATIONAL_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("OPERATIONAL_REQUEST_LOGS", "false")
    configured = Settings(app_env=environment, secret_key="a" * 40, _env_file=None)
    assert configured.operational_log_level == "WARNING"
    assert configured.operational_request_logs is False
    with pytest.raises(ValidationError):
        Settings(
            app_env=environment,
            secret_key="a" * 40,
            operational_log_level="DEBUG",
            _env_file=None,
        )


def test_request_logs_can_be_disabled_without_disabling_correlation(caplog):
    app = create_app(
        Settings(app_env="local", operational_request_logs=False, _env_file=None)
    )
    with (
        caplog.at_level(logging.INFO, logger="loadx.operations"),
        TestClient(app) as client,
    ):
        response = client.get("/health")
    assert uuid.UUID(response.headers["x-request-id"])
    assert not any(
        event["event"] == "HTTP_REQUEST_COMPLETED" for event in _events(caplog)
    )


def test_configuration_is_idempotent_and_fields_are_restricted():
    configure_observability("INFO")
    configure_observability("INFO")
    for name in ("loadx.operations", "loadx.security"):
        assert (
            sum(
                getattr(handler, "loadx_stdout", False)
                for handler in logging.getLogger(name).handlers
            )
            == 1
        )
    with pytest.raises(ValueError):
        emit_operational_event(OperationalEvent.HTTP_REQUEST_FAILED, password="secret")
    with pytest.raises(TypeError):
        emit_operational_event(
            OperationalEvent.HTTP_REQUEST_FAILED, reason={"password": "secret"}
        )
