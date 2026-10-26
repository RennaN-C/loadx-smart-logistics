"""Provider tests use synthetic HTTP only; never call Groq."""

import io
import json
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest
from app.core.config import Settings
from app.integrations.ai import AIProviderTimeoutError, AIProviderUnavailableError
from app.integrations.ai.groq import GroqProvider
from pydantic import SecretStr


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
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", lambda *_: opener)
    result = GroqProvider(config()).complete(
        [{"role": "user", "content": "Pergunta fictícia"}], timeout_seconds=2
    )
    request = opener.open.call_args.args[0]
    assert request.full_url == "https://api.groq.com/openai/v1/chat/completions"
    assert opener.open.call_args.kwargs["timeout"] == 2
    payload = json.loads(request.data)
    assert payload["max_completion_tokens"] == 700
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
    with pytest.raises(expected) as caught:
        GroqProvider(config()).complete([], timeout_seconds=1)
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
    with pytest.raises(AIProviderUnavailableError):
        GroqProvider(config()).complete([], timeout_seconds=1)


def test_missing_secret_never_opens_network(monkeypatch):
    open_network = Mock()
    monkeypatch.setattr("app.integrations.ai.groq.build_opener", open_network)
    instance = config()
    instance.groq_api_key = None
    with pytest.raises(AIProviderUnavailableError):
        GroqProvider(instance).complete([], timeout_seconds=1)
    open_network.assert_not_called()
