from collections.abc import Callable

import httpx2
import pytest
from pydantic import ValidationError

from app.integrations.viacep import (
    FakeViaCEPProvider,
    HTTPViaCEPProvider,
    ViaCEPAddress,
    ViaCEPInvalidCEPError,
    ViaCEPInvalidResponseError,
    ViaCEPNotFoundError,
    ViaCEPProvider,
    ViaCEPProviderCall,
    ViaCEPProviderError,
    ViaCEPTimeoutError,
    ViaCEPUnavailableError,
    normalize_cep,
    validate_viacep_output,
)

CEP = "01234567"
INVALID_CEPS = [
    None,
    12345678,
    True,
    b"01234567",
    "",
    "0123456",
    "012345678",
    "01234A67",
    "01234 567",
    "0123-4567",
    "01.234-567",
    "１２３４５６７８",
    "https://example.test/",
    "01234567\n/other",
]
INVALID_TIMEOUTS = [None, "5", True, 0, -1, float("inf"), float("nan")]


@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_request(*args: object, **kwargs: object) -> None:
        raise AssertionError("OC62 tests must not access the network")

    monkeypatch.setattr(httpx2.HTTPTransport, "handle_request", forbidden_request)


def external_address(**overrides: object) -> dict[str, object]:
    return {
        "cep": "01234-567",
        "logradouro": " Rua Fictícia ",
        "bairro": " Bairro Fictício ",
        "complemento": " Bloco fictício ",
        "localidade": " Cidade Fictícia ",
        "uf": "SP",
        "ibge": "ignorado",
        **overrides,
    }


def adapter_with_response(response: httpx2.Response) -> HTTPViaCEPProvider:
    return HTTPViaCEPProvider(transport=httpx2.MockTransport(lambda request: response))


@pytest.mark.parametrize("cep", [CEP, "01234-567", " 01234-567 ", "\t01234567\n"])
def test_normalizes_cep_preserving_leading_zero(cep: str) -> None:
    assert normalize_cep(cep) == CEP


@pytest.mark.parametrize("cep", INVALID_CEPS)
def test_rejects_invalid_cep(cep: object) -> None:
    with pytest.raises(ViaCEPInvalidCEPError, match="8 dígitos"):
        normalize_cep(cep)


def test_fake_returns_valid_address_and_records_only_normalized_cep_and_timeout() -> (
    None
):
    fake = FakeViaCEPProvider()
    provider: ViaCEPProvider = fake

    address = provider.lookup_address(" 01234-567 ", timeout_seconds=2.5)

    assert address == ViaCEPAddress(
        cep=CEP,
        street="Rua Fictícia",
        neighborhood="Bairro Fictício",
        city="Cidade Fictícia",
        state="SP",
    )
    assert fake.calls == [ViaCEPProviderCall(cep=CEP, timeout_seconds=2.5)]


@pytest.mark.parametrize("cep", INVALID_CEPS)
@pytest.mark.parametrize("provider_type", [FakeViaCEPProvider, HTTPViaCEPProvider])
def test_invalid_cep_never_calls_provider_or_http(
    cep: object,
    provider_type: type[FakeViaCEPProvider] | type[HTTPViaCEPProvider],
) -> None:
    calls: list[httpx2.Request] = []

    def forbidden_request(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        raise AssertionError("invalid CEP must not cause HTTP requests")

    provider = (
        HTTPViaCEPProvider(transport=httpx2.MockTransport(forbidden_request))
        if provider_type is HTTPViaCEPProvider
        else FakeViaCEPProvider()
    )
    with pytest.raises(ViaCEPInvalidCEPError):
        provider.lookup_address(cep, timeout_seconds=1.0)

    assert calls == []
    if isinstance(provider, FakeViaCEPProvider):
        assert provider.calls == []


@pytest.mark.parametrize("timeout_seconds", INVALID_TIMEOUTS)
@pytest.mark.parametrize("provider_type", [FakeViaCEPProvider, HTTPViaCEPProvider])
def test_invalid_timeout_never_calls_provider_or_http(
    timeout_seconds: float,
    provider_type: type[FakeViaCEPProvider] | type[HTTPViaCEPProvider],
) -> None:
    def forbidden_request(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("invalid timeout must not cause HTTP requests")

    provider = (
        HTTPViaCEPProvider(transport=httpx2.MockTransport(forbidden_request))
        if provider_type is HTTPViaCEPProvider
        else FakeViaCEPProvider()
    )
    with pytest.raises(ValueError, match="positive finite"):
        provider.lookup_address(CEP, timeout_seconds=timeout_seconds)
    if isinstance(provider, FakeViaCEPProvider):
        assert provider.calls == []


@pytest.mark.parametrize(
    "error_type",
    [
        ViaCEPNotFoundError,
        ViaCEPTimeoutError,
        ViaCEPUnavailableError,
        ViaCEPInvalidResponseError,
    ],
)
def test_fake_reproduces_normalized_failures(
    error_type: type[ViaCEPProviderError],
) -> None:
    error = error_type()
    provider = FakeViaCEPProvider(error=error)

    with pytest.raises(error_type) as caught:
        provider.lookup_address(CEP, timeout_seconds=1.0)

    assert caught.value is error
    assert provider.calls == [ViaCEPProviderCall(cep=CEP, timeout_seconds=1.0)]


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"cep": CEP, "city": "", "state": "SP"},
        {"cep": CEP, "city": "Cidade Fictícia", "state": "XX"},
        {"cep": "11234567", "city": "Cidade Fictícia", "state": "SP"},
    ],
)
def test_fake_validates_untrusted_output(response: object) -> None:
    provider = FakeViaCEPProvider(response=response)

    with pytest.raises(ViaCEPInvalidResponseError):
        provider.lookup_address(CEP, timeout_seconds=1.0)
    assert len(provider.calls) == 1


def test_fake_returns_configured_address_and_keeps_calls_independent() -> None:
    first = FakeViaCEPProvider(
        response={"cep": CEP, "city": "Outra Cidade Fictícia", "state": "MG"}
    )
    second = FakeViaCEPProvider()

    assert first.lookup_address(CEP, timeout_seconds=1).state == "MG"
    assert second.calls == []


def test_revalidates_instances_created_or_copied_without_validation() -> None:
    valid = ViaCEPAddress(cep=CEP, city="Cidade Fictícia", state="SP")
    for unsafe in (
        ViaCEPAddress.model_construct(cep=CEP, city="", state="XX"),
        valid.model_copy(update={"city": ""}),
    ):
        with pytest.raises(ViaCEPInvalidResponseError):
            validate_viacep_output(unsafe, requested_cep=CEP)


def test_internal_address_is_frozen_and_rejects_unknown_fields() -> None:
    address = ViaCEPAddress(cep=CEP, city="Cidade Fictícia", state="SP")
    with pytest.raises(ValidationError):
        address.city = "Alteração"
    with pytest.raises(ViaCEPInvalidResponseError):
        validate_viacep_output(
            {**address.model_dump(), "phone": "dado proibido"}, requested_cep=CEP
        )


def test_adapter_sends_only_cep_with_explicit_timeout_and_projects_useful_fields() -> (
    None
):
    calls: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        assert request.method == "GET"
        assert str(request.url) == f"https://viacep.com.br/ws/{CEP}/json/"
        assert request.url.query == b"" and request.content == b""
        assert (
            "authorization" not in request.headers and "cookie" not in request.headers
        )
        assert request.headers["accept"] == "application/json"
        assert request.extensions["timeout"] == {
            "connect": 2.5,
            "read": 2.5,
            "write": 2.5,
            "pool": 2.5,
        }
        return httpx2.Response(
            200, json=external_address(name="ignorado", phone="ignorado")
        )

    provider: ViaCEPProvider = HTTPViaCEPProvider(
        transport=httpx2.MockTransport(handle)
    )
    address = provider.lookup_address("01234-567", timeout_seconds=2.5)

    assert address.model_dump() == {
        "cep": CEP,
        "street": "Rua Fictícia",
        "neighborhood": "Bairro Fictício",
        "complement": "Bloco fictício",
        "city": "Cidade Fictícia",
        "state": "SP",
    }
    assert len(calls) == 1


@pytest.mark.parametrize("optional_value", [None, "", "   "])
def test_adapter_accepts_municipal_cep_without_optional_fields(
    optional_value: object,
) -> None:
    payload = external_address(
        logradouro=optional_value, bairro=optional_value, complemento=optional_value
    )
    provider = adapter_with_response(httpx2.Response(200, json=payload))

    address = provider.lookup_address(CEP, timeout_seconds=1.0)

    assert address.street is address.neighborhood is address.complement is None


def test_adapter_accepts_missing_optional_fields() -> None:
    provider = adapter_with_response(
        httpx2.Response(
            200, json={"cep": CEP, "localidade": "Cidade Fictícia", "uf": "SP"}
        )
    )
    assert provider.lookup_address(CEP, timeout_seconds=1.0).street is None


@pytest.mark.parametrize("error_flag", [True, "true"])
def test_adapter_reports_nonexistent_cep(error_flag: object) -> None:
    provider = adapter_with_response(httpx2.Response(200, json={"erro": error_flag}))
    with pytest.raises(ViaCEPNotFoundError):
        provider.lookup_address(CEP, timeout_seconds=1.0)


@pytest.mark.parametrize("status_code", [301, 400, 404, 429, 500, 503])
def test_adapter_normalizes_unsuccessful_http_status(status_code: int) -> None:
    provider = adapter_with_response(
        httpx2.Response(status_code, text="detalhe interno")
    )
    with pytest.raises(ViaCEPUnavailableError) as caught:
        provider.lookup_address(CEP, timeout_seconds=1.0)
    assert "detalhe interno" not in str(caught.value)


def test_adapter_does_not_follow_redirects() -> None:
    calls: list[httpx2.Request] = []

    def redirect(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return httpx2.Response(302, headers={"Location": "https://example.test/"})

    provider = HTTPViaCEPProvider(transport=httpx2.MockTransport(redirect))
    with pytest.raises(ViaCEPUnavailableError):
        provider.lookup_address(CEP, timeout_seconds=1.0)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "external_error, normalized_error",
    [
        (httpx2.ConnectTimeout, ViaCEPTimeoutError),
        (httpx2.ReadTimeout, ViaCEPTimeoutError),
        (httpx2.WriteTimeout, ViaCEPTimeoutError),
        (httpx2.PoolTimeout, ViaCEPTimeoutError),
        (httpx2.ConnectError, ViaCEPUnavailableError),
        (httpx2.RemoteProtocolError, ViaCEPUnavailableError),
        (httpx2.DecodingError, ViaCEPInvalidResponseError),
    ],
)
def test_adapter_normalizes_transport_errors_without_leaking_details(
    external_error: Callable[..., httpx2.RequestError],
    normalized_error: type[ViaCEPProviderError],
) -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise external_error("detalhe interno secreto", request=request)

    provider = HTTPViaCEPProvider(transport=httpx2.MockTransport(fail))
    with pytest.raises(normalized_error) as caught:
        provider.lookup_address(CEP, timeout_seconds=1.0)
    assert str(caught.value) == normalized_error.message
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


@pytest.mark.parametrize("body", [b"not json", b"{", b"\xff"])
def test_adapter_rejects_invalid_json(body: bytes) -> None:
    provider = adapter_with_response(httpx2.Response(200, content=body))
    with pytest.raises(ViaCEPInvalidResponseError):
        provider.lookup_address(CEP, timeout_seconds=1.0)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "texto",
        123,
        True,
        {},
        {"erro": False},
        {"erro": 1},
        {"erro": "false"},
        external_address(cep=None),
        external_address(cep="11234567"),
        external_address(cep="01234A67"),
        external_address(cep=12345678),
        external_address(localidade=None),
        external_address(localidade=" "),
        external_address(localidade=123),
        external_address(uf=None),
        external_address(uf="XX"),
        external_address(uf="sp"),
        external_address(logradouro=123),
        external_address(bairro=[]),
        external_address(complemento={}),
    ],
)
def test_adapter_rejects_invalid_or_incomplete_external_response(
    payload: object,
) -> None:
    provider = adapter_with_response(httpx2.Response(200, json=payload))
    with pytest.raises(ViaCEPInvalidResponseError) as caught:
        provider.lookup_address(CEP, timeout_seconds=1.0)
    assert str(caught.value) == ViaCEPInvalidResponseError.message


@pytest.mark.parametrize("missing_field", ["cep", "localidade", "uf"])
def test_adapter_rejects_missing_required_address_fields(missing_field: str) -> None:
    payload = external_address()
    del payload[missing_field]
    provider = adapter_with_response(httpx2.Response(200, json=payload))
    with pytest.raises(ViaCEPInvalidResponseError):
        provider.lookup_address(CEP, timeout_seconds=1.0)


@pytest.mark.parametrize(
    "error_type, code",
    [
        (ViaCEPInvalidCEPError, "VIACEP_INVALID_CEP"),
        (ViaCEPNotFoundError, "VIACEP_NOT_FOUND"),
        (ViaCEPTimeoutError, "VIACEP_TIMEOUT"),
        (ViaCEPUnavailableError, "VIACEP_UNAVAILABLE"),
        (ViaCEPInvalidResponseError, "VIACEP_INVALID_RESPONSE"),
    ],
)
def test_normalized_error_contract(
    error_type: type[ViaCEPProviderError], code: str
) -> None:
    error = error_type()
    assert isinstance(error, ViaCEPProviderError)
    assert error.code == code and str(error) == error.message
