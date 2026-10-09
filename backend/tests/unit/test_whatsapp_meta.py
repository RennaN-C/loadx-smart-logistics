import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC
from threading import Event

import httpx2
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.whatsapp.errors import WhatsAppErrorCode, WhatsAppProviderError
from app.integrations.whatsapp.factory import create_whatsapp_provider
from app.integrations.whatsapp.idempotency import InMemorySendGuard
from app.integrations.whatsapp.provider import (
    IncomingWhatsAppMessage,
    MockWhatsAppProvider,
    OutgoingWhatsAppMessage,
    get_mock_whatsapp_provider,
    mock_whatsapp_provider,
)

TOKEN = "fictional-test-token-never-valid"
NUMBER_ID = "000000000001"
PHONE = "+5500000000000"
BODY = "Mensagem fictícia de teste."
SUCCESS = {"messaging_product": "whatsapp", "messages": [{"id": "wamid.fictional"}]}


@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("OC82 tests must never access the network")

    monkeypatch.setattr(httpx2.HTTPTransport, "handle_request", forbidden)


def configuration(**overrides: object) -> Settings:
    return Settings(
        **{
            "app_env": "local",
            "database_url": "postgresql+psycopg://localhost/loadx",
            "whatsapp_provider": "meta",
            "whatsapp_real_enabled": True,
            "whatsapp_access_token": TOKEN,
            "whatsapp_phone_number_id": NUMBER_ID,
            "whatsapp_api_version": "v99.0",  # fictitious; not a supported-version claim
            "whatsapp_retry_backoff_seconds": 0,
            **overrides,
        },
        _env_file=None,
    )


def outgoing(**overrides: object) -> OutgoingWhatsAppMessage:
    return OutgoingWhatsAppMessage(
        **{"recipient_phone": PHONE, "content": BODY, **overrides}
    )


def test_send_uses_bearer_fixed_host_and_normalizes_acceptance() -> None:
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        assert request.method == "POST"
        assert (
            str(request.url) == f"https://graph.facebook.com/v99.0/{NUMBER_ID}/messages"
        )
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        assert request.extensions["timeout"] == dict.fromkeys(
            ("connect", "read", "write", "pool"), 5.0
        )
        assert json.loads(request.content) == {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": PHONE[1:],
            "type": "text",
            "text": {"preview_url": False, "body": BODY},
        }
        return httpx2.Response(200, json=SUCCESS)

    provider = create_whatsapp_provider(
        configuration(), transport=httpx2.MockTransport(handler)
    )
    original = outgoing()
    receipt = provider.send_response(original)
    assert len(calls) == 1
    assert receipt.provider_message_id == "wamid.fictional"
    assert receipt.accepted_at.tzinfo == UTC
    assert receipt.sent_at == original.sent_at
    assert original.accepted_at is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"whatsapp_real_enabled": False},
        {"whatsapp_access_token": ""},
        {"whatsapp_access_token": "invalid token\n"},
        {"whatsapp_phone_number_id": ""},
        {"whatsapp_phone_number_id": "../another-host"},
        {"whatsapp_api_version": ""},
        {"whatsapp_api_version": "v99.0/path?token=secret"},
        {"whatsapp_country_code": "0"},
    ],
)
def test_invalid_or_missing_configuration_fails_closed(overrides: dict) -> None:
    with pytest.raises(WhatsAppProviderError) as caught:
        create_whatsapp_provider(configuration(**overrides))
    assert caught.value.code == WhatsAppErrorCode.NOT_CONFIGURED
    assert TOKEN not in str(caught.value)


@pytest.mark.parametrize(
    "overrides",
    [
        {"whatsapp_provider": "unapproved"},
        {"whatsapp_timeout_seconds": 0},
        {"whatsapp_timeout_seconds": float("inf")},
        {"whatsapp_timeout_seconds": float("nan")},
        {"whatsapp_max_attempts": 0},
        {"whatsapp_max_attempts": 4},
        {"whatsapp_retry_backoff_seconds": -1},
    ],
)
def test_environment_bounds_reject_invalid_values(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        configuration(**overrides)


def test_configuration_reads_secrets_only_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", TOKEN)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", NUMBER_ID)
    configured = Settings(app_env="local", _env_file=None)
    assert configured.whatsapp_access_token.get_secret_value() == TOKEN
    assert configured.whatsapp_phone_number_id == NUMBER_ID
    assert TOKEN not in repr(configured)
    assert NUMBER_ID not in repr(configured)
    assert configured.whatsapp_provider == "mock"
    assert configured.whatsapp_real_enabled is False


@pytest.mark.parametrize(
    "status,code,uncertain",
    [
        (400, WhatsAppErrorCode.REJECTED, False),
        (401, WhatsAppErrorCode.AUTHENTICATION_FAILED, False),
        (403, WhatsAppErrorCode.AUTHENTICATION_FAILED, False),
        (404, WhatsAppErrorCode.REJECTED, False),
        (408, WhatsAppErrorCode.UNAVAILABLE, True),
        (429, WhatsAppErrorCode.RATE_LIMITED, False),
        (500, WhatsAppErrorCode.UNAVAILABLE, True),
        (503, WhatsAppErrorCode.UNAVAILABLE, True),
        (302, WhatsAppErrorCode.REJECTED, False),
    ],
)
def test_http_errors_are_sanitized_and_never_blindly_retried(status, code, uncertain):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(
            status,
            json={"error": {"message": TOKEN + PHONE + BODY}},
            headers={"Location": "https://other.example.test/", "Retry-After": "1"},
        )

    provider = create_whatsapp_provider(
        configuration(), transport=httpx2.MockTransport(handler)
    )
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing())
    assert len(calls) == 1
    assert caught.value.code == code
    assert caught.value.delivery_uncertain == uncertain
    assert TOKEN not in str(caught.value)


@pytest.mark.parametrize(
    "error_type", [httpx2.ReadTimeout, httpx2.WriteTimeout, httpx2.ReadError]
)
def test_ambiguous_transport_failure_does_not_retry(error_type):
    calls = []

    def handler(request):
        calls.append(request)
        raise error_type(TOKEN + PHONE, request=request)

    provider = create_whatsapp_provider(
        configuration(), transport=httpx2.MockTransport(handler)
    )
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing())
    assert len(calls) == 1
    assert caught.value.delivery_uncertain is True
    assert TOKEN not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize(
    "error_type", [httpx2.ConnectTimeout, httpx2.PoolTimeout, httpx2.ConnectError]
)
def test_retries_only_failures_before_transmission(error_type, monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr("app.integrations.whatsapp.meta.time.sleep", sleeps.append)

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            raise error_type(TOKEN, request=request)
        return httpx2.Response(200, json=SUCCESS)

    provider = create_whatsapp_provider(
        configuration(whatsapp_max_attempts=3, whatsapp_retry_backoff_seconds=0.5),
        transport=httpx2.MockTransport(handler),
    )
    assert provider.send_response(outgoing()).provider_message_id == "wamid.fictional"
    assert len(calls) == 3
    assert sleeps == [0.5, 1.0]


def test_connection_retries_stop_at_configured_limit():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx2.ConnectTimeout(TOKEN, request=request)

    provider = create_whatsapp_provider(
        configuration(), transport=httpx2.MockTransport(handler)
    )
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing())
    assert caught.value.code == WhatsAppErrorCode.TIMEOUT
    assert caught.value.delivery_uncertain is False
    assert len(calls) == 2


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"messages": []},
        {"messages": [{"id": "fake"}]},
        {
            "messaging_product": "whatsapp",
            "messages": [{"id": "wamid.a"}, {"id": "wamid.b"}],
        },
    ],
)
def test_invalid_acceptance_is_uncertain_and_not_retried(payload):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(200, json=payload)

    provider = create_whatsapp_provider(
        configuration(), transport=httpx2.MockTransport(handler)
    )
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing())
    assert caught.value.code == WhatsAppErrorCode.INVALID_RESPONSE
    assert caught.value.delivery_uncertain is True
    assert len(calls) == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"content": ""},
        {"content": " "},
        {"content": "x" * 4097},
        {"recipient_phone": ""},
        {"recipient_phone": "+0"},
        {"recipient_phone": "11900000000"},
        {"operation_id": "not-a-uuid"},
    ],
)
def test_invalid_message_never_reaches_transport(overrides):
    provider = create_whatsapp_provider(configuration())
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing(**overrides))
    assert caught.value.code == WhatsAppErrorCode.INVALID_MESSAGE


def test_national_phone_requires_explicit_country_code():
    calls = []

    def handler(request):
        calls.append(json.loads(request.content)["to"])
        return httpx2.Response(200, json=SUCCESS)

    provider = create_whatsapp_provider(
        configuration(whatsapp_country_code="55"),
        transport=httpx2.MockTransport(handler),
    )
    provider.send_response(outgoing(recipient_phone="(11) 90000-0000"))
    assert calls == ["5511900000000"]


def test_fake_selection_requires_no_credentials_or_network():
    assert (
        create_whatsapp_provider(
            configuration(
                whatsapp_provider="mock",
                whatsapp_real_enabled=False,
                whatsapp_access_token="",
            )
        )
        is mock_whatsapp_provider
    )
    assert get_mock_whatsapp_provider() is mock_whatsapp_provider


def test_real_provider_does_not_receive_or_execute_commands():
    provider = create_whatsapp_provider(configuration())
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.receive_message(
            IncomingWhatsAppMessage(sender_phone=PHONE, content="INICIAR VIAGEM")
        )
    assert caught.value.code == WhatsAppErrorCode.INCOMING_UNSUPPORTED


def test_real_idempotent_send_without_guard_is_denied_before_io():
    provider = create_whatsapp_provider(configuration())
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing(operation_id=uuid.uuid4()))
    assert caught.value.code == WhatsAppErrorCode.IDEMPOTENCY_UNAVAILABLE


def test_same_operation_returns_original_receipt_and_conflicting_payload_is_denied():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(200, json=SUCCESS)

    # In-memory guard is a test double, not production composition.
    provider = create_whatsapp_provider(
        configuration(),
        transport=httpx2.MockTransport(handler),
        send_guard=InMemorySendGuard(),
    )
    message = outgoing(operation_id=uuid.uuid4())
    first = provider.send_response(message)
    assert provider.send_response(replace(message)) is first
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(replace(message, content="Outro conteúdo fictício."))
    assert caught.value.code == WhatsAppErrorCode.IDENTITY_CONFLICT
    assert len(calls) == 1


def test_reservation_blocks_replay_after_ambiguous_failure():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx2.ReadTimeout(TOKEN, request=request)

    provider = create_whatsapp_provider(
        configuration(),
        transport=httpx2.MockTransport(handler),
        send_guard=InMemorySendGuard(),
    )
    message = outgoing(operation_id=uuid.uuid4())
    with pytest.raises(WhatsAppProviderError):
        provider.send_response(message)
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(message)
    assert caught.value.code == WhatsAppErrorCode.SEND_IN_DOUBT
    assert len(calls) == 1


def test_concurrent_duplicate_does_not_issue_second_post():
    entered, release = Event(), Event()
    calls = []

    def handler(request):
        calls.append(request)
        entered.set()
        assert release.wait(5)
        return httpx2.Response(200, json=SUCCESS)

    provider = create_whatsapp_provider(
        configuration(),
        transport=httpx2.MockTransport(handler),
        send_guard=InMemorySendGuard(),
    )
    message = outgoing(operation_id=uuid.uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(provider.send_response, message)
        try:
            assert entered.wait(5)
            with pytest.raises(WhatsAppProviderError) as caught:
                provider.send_response(message)
            assert caught.value.code == WhatsAppErrorCode.SEND_IN_DOUBT
        finally:
            release.set()
        receipt = first.result(timeout=5)
    assert provider.send_response(message) is receipt
    assert len(calls) == 1


def test_guard_failure_before_send_blocks_io_and_after_send_blocks_replay():
    class BrokenGuard(InMemorySendGuard):
        def complete(self, operation_id, receipt):
            raise RuntimeError(TOKEN)

    guard = BrokenGuard()
    provider = create_whatsapp_provider(
        configuration(),
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(200, json=SUCCESS)
        ),
        send_guard=guard,
    )
    message = outgoing(operation_id=uuid.uuid4())
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(message)
    assert caught.value.code == WhatsAppErrorCode.SEND_IN_DOUBT
    with pytest.raises(WhatsAppProviderError, match="SEND_IN_DOUBT"):
        provider.send_response(message)
    assert TOKEN not in str(caught.value)


def test_fake_idempotency_is_available_without_real_credentials():
    provider = MockWhatsAppProvider()
    message = outgoing(operation_id=uuid.uuid4())
    assert provider.send_response(message) is message
    assert provider.send_response(message) is message
    assert provider.sent_messages == [message]


def test_logs_and_repr_do_not_expose_sensitive_input_or_provider_body(caplog):
    def handler(request):
        logging.getLogger("httpcore2.http11").debug(TOKEN + PHONE + BODY)
        return httpx2.Response(401, json={"error": {"message": TOKEN + BODY}})

    provider = create_whatsapp_provider(
        configuration(), transport=httpx2.MockTransport(handler)
    )
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(WhatsAppProviderError):
            provider.send_response(outgoing())
        logging.getLogger("httpx2").info("unrelated-http-log")
    assert "WHATSAPP_SEND_FAILED" in caplog.text
    assert "unrelated-http-log" in caplog.text
    for value in (TOKEN, PHONE, BODY, NUMBER_ID):
        assert value not in caplog.text
        assert value not in repr(outgoing())


@pytest.mark.parametrize(
    "provider_code,expected",
    [
        (190, WhatsAppErrorCode.AUTHENTICATION_FAILED),
        (4, WhatsAppErrorCode.RATE_LIMITED),
        (80007, WhatsAppErrorCode.RATE_LIMITED),
        (130429, WhatsAppErrorCode.RATE_LIMITED),
        (131048, WhatsAppErrorCode.RATE_LIMITED),
        (131056, WhatsAppErrorCode.RATE_LIMITED),
        (131047, WhatsAppErrorCode.REJECTED),
        ("190", WhatsAppErrorCode.REJECTED),
    ],
)
def test_graph_codes_in_http_400_are_normalized_without_provider_text(
    provider_code, expected
):
    provider = create_whatsapp_provider(
        configuration(),
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(
                400, json={"error": {"code": provider_code, "message": TOKEN}}
            )
        ),
    )
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing())
    assert caught.value.code == expected
    assert TOKEN not in str(caught.value)


def test_claim_storage_failure_prevents_transmission():
    class BrokenClaim:
        def claim(self, operation_id, fingerprint):
            raise RuntimeError(TOKEN)

        def complete(self, operation_id, receipt):
            raise AssertionError("must not complete failed claim")

    provider = create_whatsapp_provider(configuration(), send_guard=BrokenClaim())
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing(operation_id=uuid.uuid4()))
    assert caught.value.code == WhatsAppErrorCode.IDEMPOTENCY_UNAVAILABLE
    assert TOKEN not in str(caught.value)


def test_malformed_json_success_is_uncertain():
    provider = create_whatsapp_provider(
        configuration(),
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(200, content=b"not-json")
        ),
    )
    with pytest.raises(WhatsAppProviderError) as caught:
        provider.send_response(outgoing())
    assert caught.value.code == WhatsAppErrorCode.INVALID_RESPONSE
    assert caught.value.delivery_uncertain is True


def test_guard_capacity_does_not_evict_success_and_allow_duplicate():
    guard = InMemorySendGuard(capacity=1)
    identity = uuid.uuid4()
    message = outgoing(operation_id=identity)
    assert guard.claim(identity, "fingerprint") is None
    guard.complete(identity, message)
    with pytest.raises(WhatsAppProviderError, match="IDEMPOTENCY_UNAVAILABLE"):
        guard.claim(uuid.uuid4(), "another")
    assert guard.claim(identity, "fingerprint") is message
