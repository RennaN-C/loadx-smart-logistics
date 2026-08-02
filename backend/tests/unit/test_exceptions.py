import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import LogCaptureFixture

from app.core.exceptions import register_exception_handlers

SENSITIVE_ERROR_MESSAGE = "database-password=should-not-leak"


def build_test_app() -> FastAPI:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/unexpected")
    def raise_unexpected_error() -> None:
        raise RuntimeError(SENSITIVE_ERROR_MESSAGE)

    return test_app


def test_unexpected_error_returns_safe_standard_response(
    caplog: LogCaptureFixture,
) -> None:
    test_app = build_test_app()
    client = TestClient(test_app, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR, logger="app.core.exceptions"):
        response = client.get("/unexpected?token=should-not-leak")

    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "Ocorreu um erro interno inesperado.",
        "details": [],
    }
    assert SENSITIVE_ERROR_MESSAGE not in response.text
    assert "token=should-not-leak" not in response.text

    assert len(caplog.records) == 1
    log_message = caplog.records[0].getMessage()
    assert "method=GET" in log_message
    assert "path=/unexpected" in log_message
    assert "exception_type=RuntimeError" in log_message
    assert SENSITIVE_ERROR_MESSAGE not in log_message
    assert "token=should-not-leak" not in log_message
    assert caplog.records[0].exc_info is None
