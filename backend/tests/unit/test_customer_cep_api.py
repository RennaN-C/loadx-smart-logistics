from collections.abc import Generator

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.integrations.viacep import (
    FakeViaCEPProvider,
    HTTPViaCEPProvider,
    ViaCEPInvalidCEPError,
    ViaCEPInvalidResponseError,
    ViaCEPNotFoundError,
    ViaCEPProviderCall,
    ViaCEPProviderError,
    ViaCEPTimeoutError,
    ViaCEPUnavailableError,
)
from app.main import create_app
from app.modules.auth.dependencies import get_auth_session_service, get_current_user
from app.modules.customers import router as customer_router
from app.modules.users.models import User

CEP = "01234567"
ADDRESS = {
    "cep": CEP,
    "street": "Rua Fictícia",
    "neighborhood": "Bairro Fictício",
    "complement": None,
    "city": "Cidade Fictícia",
    "state": "SP",
}
TEXT_LIMITS = [
    ("street", 255),
    ("neighborhood", 255),
    ("complement", 255),
    ("city", 120),
]


@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_request(*args: object, **kwargs: object) -> None:
        raise AssertionError("OC62 API tests must not access the network")

    monkeypatch.setattr(httpx2.HTTPTransport, "handle_request", forbidden_request)


@pytest.fixture
def provider() -> FakeViaCEPProvider:
    return FakeViaCEPProvider(response=ADDRESS)


@pytest.fixture
def api(provider: FakeViaCEPProvider) -> FastAPI:
    application = create_app()

    def forbidden_database() -> None:
        raise AssertionError("CEP lookup must not access the customer database")

    application.dependency_overrides[get_db] = forbidden_database
    application.dependency_overrides[get_current_user] = lambda: User(
        role="LOGISTICS_MANAGER", active=True
    )
    application.dependency_overrides[customer_router.get_viacep_provider] = lambda: (
        provider
    )
    return application


@pytest.fixture
def client(api: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(api) as test_client:
        yield test_client


@pytest.mark.parametrize("cep", [CEP, "01234-567"])
def test_cep_lookup_returns_address_and_normalizes_before_provider(
    client: TestClient, provider: FakeViaCEPProvider, cep: str
) -> None:
    response = client.get(f"/api/v1/customers/cep/{cep}")

    assert response.status_code == 200
    assert response.json() == ADDRESS
    assert provider.calls == [ViaCEPProviderCall(cep=CEP, timeout_seconds=5.0)]


@pytest.mark.parametrize("role", ["ADMIN", "CHECKER", "DRIVER"])
def test_cep_lookup_rejects_roles_other_than_logistics_manager(
    api: FastAPI, client: TestClient, provider: FakeViaCEPProvider, role: str
) -> None:
    api.dependency_overrides[get_current_user] = lambda: User(role=role, active=True)

    response = client.get(f"/api/v1/customers/cep/{CEP}")

    assert response.status_code == 403
    assert response.json() == {
        "code": "AUTH_FORBIDDEN",
        "message": "Usuário sem permissão para esta ação.",
        "details": [],
    }
    assert provider.calls == []


def test_cep_lookup_requires_authentication(
    api: FastAPI, client: TestClient, provider: FakeViaCEPProvider
) -> None:
    del api.dependency_overrides[get_current_user]
    api.dependency_overrides[get_auth_session_service] = object

    response = client.get(f"/api/v1/customers/cep/{CEP}")

    assert response.status_code == 401
    assert response.json() == {
        "code": "AUTH_INVALID_TOKEN",
        "message": "Sessão ausente ou inválida.",
        "details": [],
    }
    assert provider.calls == []


@pytest.mark.parametrize("cep", ["123", "01234A67"])
def test_invalid_cep_does_not_invoke_provider(
    client: TestClient,
    provider: FakeViaCEPProvider,
    monkeypatch: pytest.MonkeyPatch,
    cep: str,
) -> None:
    def forbidden_lookup(*args: object, **kwargs: object) -> None:
        raise AssertionError("Invalid CEP must be rejected before the provider call")

    monkeypatch.setattr(provider, "lookup_address", forbidden_lookup)

    response = client.get(f"/api/v1/customers/cep/{cep}")

    assert response.status_code == 422
    assert response.json() == {
        "code": "VIACEP_INVALID_CEP",
        "message": "Informe um CEP com 8 dígitos.",
        "details": [{"field": "cep"}],
    }


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ViaCEPInvalidCEPError(), 422),
        (ViaCEPNotFoundError(), 404),
        (ViaCEPTimeoutError(), 504),
        (ViaCEPUnavailableError(), 503),
        (ViaCEPInvalidResponseError(), 502),
    ],
)
def test_cep_lookup_uses_normalized_error_envelope(
    client: TestClient,
    provider: FakeViaCEPProvider,
    error: ViaCEPProviderError,
    expected_status: int,
) -> None:
    provider.error = error

    response = client.get(f"/api/v1/customers/cep/{CEP}")

    assert response.status_code == expected_status
    assert response.json() == {
        "code": error.code,
        "message": error.message,
        "details": [{"field": "cep"}] if expected_status == 422 else [],
    }


@pytest.mark.parametrize("field,limit", TEXT_LIMITS)
def test_cep_lookup_accepts_text_at_customer_compatible_limits(
    client: TestClient, provider: FakeViaCEPProvider, field: str, limit: int
) -> None:
    provider.response = {**ADDRESS, field: "A" * limit}

    response = client.get(f"/api/v1/customers/cep/{CEP}")

    assert response.status_code == 200
    assert response.json()[field] == "A" * limit


@pytest.mark.parametrize("field,limit", TEXT_LIMITS)
def test_cep_lookup_rejects_external_text_above_customer_compatible_limits(
    client: TestClient, provider: FakeViaCEPProvider, field: str, limit: int
) -> None:
    provider.response = {**ADDRESS, field: "A" * (limit + 1)}

    response = client.get(f"/api/v1/customers/cep/{CEP}")

    assert response.status_code == 502
    assert response.json() == {
        "code": "VIACEP_INVALID_RESPONSE",
        "message": ViaCEPInvalidResponseError.message,
        "details": [],
    }


def test_cep_lookup_rejects_incomplete_external_address(
    client: TestClient, provider: FakeViaCEPProvider
) -> None:
    provider.response = {"cep": CEP, "state": "SP"}

    response = client.get(f"/api/v1/customers/cep/{CEP}")

    assert response.status_code == 502
    assert response.json()["code"] == "VIACEP_INVALID_RESPONSE"


def test_default_provider_dependency_uses_adapter_with_mocked_http(
    api: FastAPI, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests: list[httpx2.Request] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "cep": "01234-567",
                "logradouro": ADDRESS["street"],
                "bairro": ADDRESS["neighborhood"],
                "complemento": "",
                "localidade": ADDRESS["city"],
                "uf": ADDRESS["state"],
            },
        )

    del api.dependency_overrides[customer_router.get_viacep_provider]
    monkeypatch.setattr(
        customer_router,
        "HTTPViaCEPProvider",
        lambda: HTTPViaCEPProvider(transport=httpx2.MockTransport(respond)),
    )

    response = client.get("/api/v1/customers/cep/01234-567")

    assert response.status_code == 200
    assert response.json() == ADDRESS
    assert len(requests) == 1
    assert str(requests[0].url) == f"https://viacep.com.br/ws/{CEP}/json/"
    assert requests[0].extensions["timeout"] == {
        "connect": 5.0,
        "read": 5.0,
        "write": 5.0,
        "pool": 5.0,
    }
