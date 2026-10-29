"""Provider tests use synthetic HTTP only; never call Groq."""

import io
import json
import ssl
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.ai import AIProviderTimeoutError, AIProviderUnavailableError
from app.integrations.ai.groq import AIProviderToolGenerationError, GroqProvider


def config(**overrides):
    return Settings(
        app_env="local",
        database_url="postgresql+psycopg://localhost/test",
        ai_provider="groq",
        groq_api_key=SecretStr("fictitious-test-key"),
        **overrides,
    )


def test_groq_fixed_endpoint_and_bounded_payload(monkeypatch):
    reply = {
        "choices": [
            {"message": {"role": "assistant", "content": "Resposta em português."}}
        ]
    }
    response = io.BytesIO(json.dumps(reply).encode())
    opener = Mock()
    opener.open.return_value = response
    handlers = []

    def capture_handlers(*items):
        handlers.extend(items)
        return opener

    monkeypatch.setattr("app.integrations.ai.groq.build_opener", capture_handlers)
    result = GroqProvider(config()).complete(
        [{"role": "user", "content": "Pergunta fictícia"}], timeout_seconds=2
    )
    tls = handlers[1]._context
    assert tls.verify_mode == ssl.CERT_REQUIRED
    assert tls.check_hostname is True
    request = opener.open.call_args.args[0]
    assert request.full_url == "https://api.groq.com/openai/v1/chat/completions"
    assert request.get_header("User-agent") == "LoadX-Smart-Logistics/1.2"
    assert "Python-urllib" not in request.get_header("User-agent")
    assert opener.open.call_args.kwargs["timeout"] == 2
    payload = json.loads(request.data)
    assert payload["max_completion_tokens"] == 2048
    assert "tools" not in payload
    assert result == {"role": "assistant", "content": "Resposta em português."}


@pytest.mark.parametrize(
    "error,expected",
    [
        (TimeoutError(), AIProviderTimeoutError),
        (
            HTTPError("https://example.invalid", 429, "private body", {}, None),
            AIProviderUnavailableError,
        ),
        (
            HTTPError("https://example.invalid", 503, "private body", {}, None),
            AIProviderUnavailableError,
        ),
    ],
)
def test_groq_normalizes_failures_without_raw_response(monkeypatch, error, expected):
    opener = Mock()
    opener.open.side_effect = error
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    provider = GroqProvider(config())
    with pytest.raises(expected) as caught:
        provider.complete([], timeout_seconds=1)
    assert "private body" not in str(caught.value)


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"x" * 65537,
        b'{"choices": []}',
        b'{"choices":[{"message":{"content":""}}]}',
    ],
)
def test_groq_rejects_invalid_or_excessive_response(monkeypatch, body):
    opener = Mock()
    opener.open.return_value = io.BytesIO(body)
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    provider = GroqProvider(config())
    with pytest.raises(AIProviderUnavailableError):
        provider.complete([], timeout_seconds=1)


def test_missing_secret_never_opens_network(monkeypatch):
    open_network = Mock()
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", open_network)
    instance = config()
    instance.groq_api_key = None
    provider = GroqProvider(instance)
    with pytest.raises(AIProviderUnavailableError):
        provider.complete([], timeout_seconds=1)
    open_network.assert_not_called()


def test_groq_logs_only_safe_status_on_http_error(monkeypatch, caplog):
    opener = Mock()
    opener.open.side_effect = HTTPError(
        "https://example.invalid", 401, "secret-key and private prompt", {}, None
    )
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    with pytest.raises(AIProviderUnavailableError):
        GroqProvider(config()).complete([], timeout_seconds=1)
    assert "GROQ_REQUEST_FAILURE category=http_401" in caplog.text
    assert "secret-key" not in caplog.text
    assert "private prompt" not in caplog.text


@pytest.mark.parametrize(
    "code,expected",
    [
        ("model_permission_blocked_org", "model_permission_blocked_org"),
        ("model_permission_blocked_project", "model_permission_blocked_project"),
        ("arbitrary-private-message", "unclassified"),
    ],
)
def test_groq_403_reports_only_allowlisted_error_code(
    monkeypatch, caplog, code, expected
):
    body = json.dumps(
        {"error": {"code": code, "message": "private-customer-prompt"}}
    ).encode()
    opener = Mock()
    opener.open.side_effect = HTTPError(
        "https://example.invalid", 403, "Forbidden", {}, io.BytesIO(body)
    )
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    with pytest.raises(AIProviderUnavailableError):
        GroqProvider(config()).complete([], timeout_seconds=1)
    assert f"GROQ_REQUEST_FAILURE category=http_403 reason={expected}" in caplog.text
    assert "private-customer-prompt" not in caplog.text
    assert "arbitrary-private-message" not in caplog.text


def test_groq_cloudflare_client_signature_403_logs_safe_reason(monkeypatch, caplog):
    opener = Mock()
    opener.open.side_effect = HTTPError(
        "https://example.invalid",
        403,
        "Forbidden",
        {},
        io.BytesIO(b"error code: 1010"),
    )
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    with pytest.raises(AIProviderUnavailableError):
        GroqProvider(config()).complete([], timeout_seconds=1)
    assert (
        "GROQ_REQUEST_FAILURE category=http_403 reason=edge_client_signature_1010"
        in caplog.text
    )


def test_groq_invalid_tool_generation_has_safe_retryable_category(monkeypatch, caplog):
    body = json.dumps(
        {
            "error": {
                "type": "invalid_request_error",
                "failed_generation": {
                    "reason": "tool malformed",
                    "attempted_arguments": "private-customer-token",
                },
            }
        }
    ).encode()
    opener = Mock()
    opener.open.side_effect = HTTPError(
        "https://example.invalid", 400, "Bad Request", {}, io.BytesIO(body)
    )
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    with pytest.raises(AIProviderToolGenerationError):
        GroqProvider(config()).complete([], timeout_seconds=1)
    assert "reason=invalid_tool_generation" in caplog.text
    assert "private-customer-token" not in caplog.text


def test_groq_other_http_400_fails_closed_without_tool_retry(monkeypatch):
    opener = Mock()
    opener.open.side_effect = HTTPError(
        "https://example.invalid",
        400,
        "Bad Request",
        {},
        io.BytesIO(b'{"error":{"type":"invalid_request_error"}}'),
    )
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    with pytest.raises(AIProviderUnavailableError) as caught:
        GroqProvider(config()).complete([], timeout_seconds=1)
    assert not isinstance(caught.value, AIProviderToolGenerationError)


def test_groq_enforces_json_only_for_loxi_conversation(monkeypatch):
    response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"answer":"Oi!","source_names":[]}',
                }
            }
        ]
    }
    opener = Mock()
    opener.open.return_value = io.BytesIO(json.dumps(response).encode())
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    messages = [
        {
            "role": "system",
            "content": "Você é o Loxi, assistente operacional do LoadX. Retorne JSON.",
        },
        {"role": "user", "content": "Oi Loxi"},
    ]
    GroqProvider(config(groq_model="openai/gpt-oss-120b")).complete(
        messages, timeout_seconds=2
    )
    payload = json.loads(opener.open.call_args.args[0].data)
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["reasoning_format"] == "hidden"
    assert "tools" not in payload


def test_groq_preserves_plain_explanation_and_tool_flow(monkeypatch):
    response = {
        "choices": [
            {"message": {"role": "assistant", "content": "Explicação autorizada."}}
        ]
    }
    opener = Mock()
    opener.open.side_effect = [
        io.BytesIO(json.dumps(response).encode()),
        io.BytesIO(json.dumps(response).encode()),
    ]
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    provider = GroqProvider(config(groq_model="openai/gpt-oss-120b"))
    provider.complete(
        [{"role": "system", "content": "Explique os dados técnicos."}],
        timeout_seconds=2,
    )
    provider.complete(
        [
            {
                "role": "system",
                "content": "Você é o Loxi, assistente operacional do LoadX. JSON.",
            }
        ],
        tools=[{"type": "function", "function": {"name": "get_usage_guidance"}}],
        timeout_seconds=2,
    )
    payloads = [json.loads(call.args[0].data) for call in opener.open.call_args_list]
    assert "response_format" not in payloads[0]
    assert "reasoning_format" not in payloads[0]
    assert "response_format" not in payloads[1]
    assert payloads[1]["reasoning_format"] == "hidden"
    assert payloads[1]["tool_choice"] == "auto"
