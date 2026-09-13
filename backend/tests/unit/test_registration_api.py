import uuid
from unittest.mock import Mock

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.session import get_db
from app.main import create_app
from app.modules.auth.dependencies import get_current_user
from app.modules.customers.router import get_customer_service
from app.modules.drivers.router import get_driver_service
from app.modules.users.models import User


@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize(
    ("resource", "payload", "invalid_fields"),
    [
        (
            "customers",
            {
                "name": "Cliente fictício",
                "document": "12345678908",
                "phone": "11800000000",
                "address": "Rua de Teste, 1",
                "city": "Cidade de Teste",
                "state": "SP",
            },
            {"document", "phone"},
        ),
        (
            "drivers",
            {
                "name": "Motorista fictício",
                "document": "00000000000191",
                "phone": "0130000000",
                "license_number": "12345678901",
            },
            {"document", "phone", "license_number"},
        ),
    ],
)
def test_registration_validation_uses_existing_422_envelope_before_persistence(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    resource: str,
    payload: dict[str, str],
    invalid_fields: set[str],
) -> None:
    def forbidden_access(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "Registration validation must not access database or network"
        )

    monkeypatch.setattr(httpx2.HTTPTransport, "handle_request", forbidden_access)
    application = create_app(
        Settings(
            app_env="local",
            backend_cors_origins_raw="https://app.example.test",
            _env_file=None,
        )
    )
    service = Mock()
    application.dependency_overrides[get_db] = forbidden_access
    application.dependency_overrides[get_customer_service] = lambda: service
    application.dependency_overrides[get_driver_service] = lambda: service
    application.dependency_overrides[get_current_user] = lambda: User(
        role="LOGISTICS_MANAGER", active=True
    )
    path = f"/api/v1/{resource}"
    if method == "PATCH":
        path += f"/{uuid.UUID(int=1)}"

    with TestClient(
        application, headers={"Origin": "https://app.example.test"}
    ) as client:
        response = client.request(method, path, json=payload)

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "details"}
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Os dados informados são inválidos."
    assert {detail["field"] for detail in body["details"]} == invalid_fields
    assert all(detail["type"] == "value_error" for detail in body["details"])
    assert service.mock_calls == []
