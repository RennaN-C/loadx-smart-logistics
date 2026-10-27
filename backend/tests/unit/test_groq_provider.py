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
from app.integrations.ai.groq import GroqProvider


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
