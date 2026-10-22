"""Isolated tests for Resend HTTP delivery; never contact the real provider."""

import hashlib
import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from app.core.config import Settings
from app.integrations.password_recovery.delivery import (
    dispatch_recovery,
    get_recovery_delivery,
)
from app.integrations.password_recovery.resend_delivery import (
    ResendRecoveryDelivery,
)
from app.modules.auth.totp import IdentityUnavailableError


def config(**overrides):
    values = {
        "app_env": "local",
        "password_recovery_provider": "resend",
        "password_recovery_url": "https://loadx-system.vercel.app/password-reset",
        "resend_sender": "security@example.test",
        "resend_api_key": "re_test_only_not_real",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_resend_uses_verified_https_post_and_preserves_the_branded_message(monkeypatch):
    recorded = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_open(request, *, timeout):
        recorded["url"] = request.full_url
        recorded["method"] = request.get_method()
        recorded["timeout"] = timeout
        recorded["headers"] = dict(request.header_items())
        recorded["body"] = json.loads(request.data)
        return Response()

    monkeypatch.setattr(
        "app.integrations.password_recovery.resend_delivery.urlopen", fake_open
    )
    ResendRecoveryDelivery(config()).deliver("account@example.test", "private-token")
    assert recorded["url"] == "https://api.resend.com/emails"
    assert recorded["method"] == "POST"
    assert recorded["timeout"] == 5
    assert recorded["headers"]["Authorization"] == "Bearer re_test_only_not_real"
    assert recorded["headers"]["Content-type"] == "application/json"
    assert recorded["headers"]["Idempotency-key"] == (
        "loadx-recovery-" + hashlib.sha256(b"private-token").hexdigest()
    )
    assert recorded["body"]["to"] == ["account@example.test"]
    assert "security@example.test" in recorded["body"]["from"]
    assert recorded["body"]["subject"] == "LoadX | Redefinição de senha"
    assert "#token=private-token" in recorded["body"]["text"]
    assert "#token=private-token" in recorded["body"]["html"]
    assert "Redefinir minha senha" in recorded["body"]["html"]
    assert "re_test_only_not_real" not in json.dumps(recorded["body"])


@pytest.mark.parametrize(
    "overrides",
    [
        {"password_recovery_provider": "none"},
        {"resend_api_key": None},
        {"resend_api_key": ""},
        {"resend_api_key": "not_a_key"},
        {"resend_sender": None},
        {"resend_sender": "onboarding@evil.test\nBcc: external@example.test"},
        {"resend_sender": "abc@example.test,external@example.test"},
        {"password_recovery_url": "http://loadx-system.vercel.app/password-reset"},
        {"password_recovery_url": "https://evil.test/reset?next=foo"},
        {"password_recovery_url": "https://user:pass@example.test/reset"},
        {"password_recovery_url": "https://example.test/reset#token=bad"},
        {"password_recovery_url": "https://example.test\\@evil.test/reset"},
        {"password_recovery_url": "https://example.test:bad/reset"},
    ],
)
def test_resend_configuration_fails_closed(overrides):
    with pytest.raises(IdentityUnavailableError):
        ResendRecoveryDelivery(config(**overrides))


def test_resend_factory_selects_only_explicit_provider(monkeypatch):
    import app.integrations.password_recovery.delivery as delivery_module

    settings = config()
    monkeypatch.setattr(delivery_module, "settings", settings)
    assert isinstance(get_recovery_delivery(), ResendRecoveryDelivery)
    settings.password_recovery_provider = "none"
    with pytest.raises(IdentityUnavailableError):
        get_recovery_delivery()


def test_resend_error_is_sanitized_without_token_or_provider_response(monkeypatch, caplog):
    def failing_open(request, *, timeout):
        raise HTTPError(
            request.full_url,
            422,
            "private-token and secret provider message",
            {},
            BytesIO(b"private-token"),
        )

    monkeypatch.setattr(
        "app.integrations.password_recovery.resend_delivery.urlopen", failing_open
    )
    dispatch_recovery(
        ResendRecoveryDelivery(config()), "private@example.test", "private-token"
    )
    assert "AUTH_RECOVERY_DELIVERY_FAILED" in caplog.text
    assert "private-token" not in caplog.text
    assert "private@example.test" not in caplog.text
    assert "secret provider message" not in caplog.text


def test_resend_rejects_non_success_http_without_logging_payload(monkeypatch, caplog):
    class Response:
        status = 500

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        "app.integrations.password_recovery.resend_delivery.urlopen",
        lambda request, *, timeout: Response(),
    )
    dispatch_recovery(
        ResendRecoveryDelivery(config()), "private@example.test", "private-token"
    )
    assert "AUTH_RECOVERY_DELIVERY_FAILED" in caplog.text
    assert "private-token" not in caplog.text
