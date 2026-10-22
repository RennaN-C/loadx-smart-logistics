"""Mailjet v3.1 recovery adapter tests; the network is always mocked."""

import base64
import json
import ssl
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from app.core.config import Settings
from app.integrations.password_recovery.delivery import (
    dispatch_recovery,
    get_recovery_delivery,
)
from app.integrations.password_recovery.mailjet_delivery import (
    MailjetRecoveryDelivery,
)
from app.modules.auth.totp import IdentityUnavailableError


def config(**overrides):
    values = {
        "app_env": "local",
        "password_recovery_provider": "mailjet",
        "password_recovery_url": "https://loadx-system.vercel.app/password-reset",
        "mailjet_api_key": "sample-public-key",
        "mailjet_secret_key": "sample-private-key",
        "mailjet_sender": "validated@example.test",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def accepted_response(status=200, message_status="success"):
    class Response:
        def __init__(self):
            self.status = status

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, size=-1):
            return json.dumps({"Messages": [{"Status": message_status}]}).encode(
                "utf-8"
            )

    return Response()


def test_mailjet_uses_https_basic_auth_and_branded_message(monkeypatch, caplog):
    recorded = {}

    def fake_open(request, *, timeout):
        recorded["url"] = request.full_url
        recorded["method"] = request.get_method()
        recorded["timeout"] = timeout
        recorded["headers"] = dict(request.header_items())
        recorded["body"] = json.loads(request.data)
        return accepted_response()

    monkeypatch.setattr(
        "app.integrations.password_recovery.mailjet_delivery.urlopen", fake_open
    )
    delivery = MailjetRecoveryDelivery(config())
    dispatch_recovery(delivery, "owner@example.test", "private-reset-token")
    assert recorded["url"] == "https://api.mailjet.com/v3.1/send"
    assert recorded["method"] == "POST"
    assert recorded["timeout"] == 5
    headers = {key.lower(): value for key, value in recorded["headers"].items()}
    assert headers["content-type"] == "application/json"
    assert headers["accept"] == "application/json"
    assert headers["authorization"].startswith("Basic ")
    assert (
        base64.b64decode(headers["authorization"][6:]).decode("utf-8")
        == "sample-public-key:sample-private-key"
    )
    body = recorded["body"]
    assert list(body) == ["Messages"]
    assert len(body["Messages"]) == 1
    msg = body["Messages"][0]
    assert msg["From"] == {
        "Email": "validated@example.test",
        "Name": "LoadX | Segurança",
    }
    assert msg["To"] == [{"Email": "owner@example.test"}]
    assert msg["Subject"] == "LoadX | Redefinição de senha"
    assert "#token=private-reset-token" in msg["TextPart"]
    assert "#token=private-reset-token" in msg["HTMLPart"]
    assert "Redefinir minha senha" in msg["HTMLPart"]
    assert "private-reset-token" not in str(recorded["headers"])
    assert "sample-private-key" not in caplog.text
    assert "owner@example.test" not in caplog.text
    assert "AUTH_RECOVERY_DELIVERY_FAILED" not in caplog.text


@pytest.mark.parametrize(
    "override",
    [
        {"password_recovery_provider": "none"},
        {"mailjet_api_key": None},
        {"mailjet_api_key": ""},
        {"mailjet_secret_key": None},
        {"mailjet_secret_key": ""},
        {"mailjet_sender": None},
        {"mailjet_sender": "bad-sender"},
        {"mailjet_sender": "one@example.test,other@example.test"},
        {"mailjet_sender": "one@example.test\\nBcc:other@example.test"},
        {"password_recovery_url": "http://example.test/reset"},
        {"password_recovery_url": "https://example.test/reset?evil=1"},
        {"password_recovery_url": "https://example.test/reset#bad"},
    ],
)
def test_mailjet_invalid_config_fails_closed(override):
    with pytest.raises(IdentityUnavailableError):
        MailjetRecoveryDelivery(config(**override))


def test_mailjet_selected_only_when_explicitly_configured(monkeypatch):
    import app.integrations.password_recovery.delivery as delivery_module

    settings = config()
    monkeypatch.setattr(delivery_module, "settings", settings)
    assert isinstance(get_recovery_delivery(), MailjetRecoveryDelivery)
    settings.password_recovery_provider = "none"
    with pytest.raises(IdentityUnavailableError):
        get_recovery_delivery()


@pytest.mark.parametrize("status", [400, 401, 403, 422, 429, 500])
def test_mailjet_http_error_reports_only_code_and_category(status, monkeypatch, caplog):
    def fake_open(request, *, timeout):
        raise HTTPError(
            request.full_url,
            status,
            "private-reset-token and provider secret",
            {},
            BytesIO(b"private-reset-token, owner@example.test"),
        )

    monkeypatch.setattr(
        "app.integrations.password_recovery.mailjet_delivery.urlopen", fake_open
    )
    dispatch_recovery(
        MailjetRecoveryDelivery(config()), "owner@example.test", "private-reset-token"
    )
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "loadx.security"
    ]
    assert len(events) == 1
    assert events[0]["event"] == "AUTH_RECOVERY_DELIVERY_FAILED"
    assert events[0]["delivery_provider"] == "mailjet"
    assert events[0]["failure_category"] == "http_rejection"
    assert events[0]["provider_http_status"] == status
    assert "private-reset-token" not in caplog.text
    assert "owner@example.test" not in caplog.text
    assert "provider secret" not in caplog.text
    assert "sample-private-key" not in caplog.text


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("timeout", "timeout"), ("tls", "tls"), ("network", "network")],
)
def test_mailjet_network_errors_are_sanitized(kind, expected, monkeypatch, caplog):
    def fake_open(request, *, timeout):
        if kind == "timeout":
            raise URLError(TimeoutError("private-reset-token timeout"))
        if kind == "tls":
            raise URLError(ssl.SSLError("private-reset-token TLS"))
        raise URLError("owner@example.test network failed")

    monkeypatch.setattr(
        "app.integrations.password_recovery.mailjet_delivery.urlopen", fake_open
    )
    dispatch_recovery(
        MailjetRecoveryDelivery(config()), "owner@example.test", "private-reset-token"
    )
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "loadx.security"
    ]
    assert events[0]["delivery_provider"] == "mailjet"
    assert events[0]["failure_category"] == expected
    assert "provider_http_status" not in events[0]
    assert "private-reset-token" not in caplog.text
    assert "owner@example.test" not in caplog.text


@pytest.mark.parametrize("status", ["error", "queued", "rejected"])
def test_mailjet_per_message_failure_is_not_reported_as_success(
    status, monkeypatch, caplog
):
    monkeypatch.setattr(
        "app.integrations.password_recovery.mailjet_delivery.urlopen",
        lambda request, *, timeout: accepted_response(message_status=status),
    )
    dispatch_recovery(
        MailjetRecoveryDelivery(config()), "owner@example.test", "private-reset-token"
    )
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "loadx.security"
    ]
    assert events[0]["delivery_provider"] == "mailjet"
    assert events[0]["failure_category"] == "provider_rejected"
    assert "private-reset-token" not in caplog.text


def test_mailjet_invalid_response_is_safely_rejected(monkeypatch, caplog):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, size=-1):
            return b"private-reset-token not JSON"

    monkeypatch.setattr(
        "app.integrations.password_recovery.mailjet_delivery.urlopen",
        lambda request, *, timeout: Response(),
    )
    dispatch_recovery(
        MailjetRecoveryDelivery(config()), "owner@example.test", "private-reset-token"
    )
    assert "provider_rejected" in caplog.text
    assert "private-reset-token" not in caplog.text


def test_mailjet_non_2xx_response_is_rejected(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.integrations.password_recovery.mailjet_delivery.urlopen",
        lambda request, *, timeout: accepted_response(status=503),
    )
    dispatch_recovery(
        MailjetRecoveryDelivery(config()), "owner@example.test", "private-reset-token"
    )
    assert '"provider_http_status":503' in caplog.text
    assert '"delivery_provider":"mailjet"' in caplog.text
    assert "private-reset-token" not in caplog.text


@pytest.mark.parametrize(
    ("override", "check"),
    [
        ({"password_recovery_provider": "none"}, "provider_mismatch"),
        ({"password_recovery_url": "http://bad.test/reset"}, "recovery_url_invalid"),
        ({"mailjet_api_key": None}, "api_key_missing"),
        ({"mailjet_secret_key": None}, "secret_key_missing"),
        ({"mailjet_sender": "not-an-address"}, "sender_invalid"),
    ],
)
def test_mailjet_invalid_settings_emit_fixed_safe_reason(override, check, caplog):
    with pytest.raises(IdentityUnavailableError):
        MailjetRecoveryDelivery(config(**override))
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "loadx.security"
    ]
    assert len(events) == 1
    assert events[0]["event"] == "AUTH_RECOVERY_CONFIG_INVALID"
    assert events[0]["delivery_provider"] == "mailjet"
    assert events[0]["failed_checks"] == check
    assert "sample-private-key" not in caplog.text
    assert "sample-public-key" not in caplog.text
    assert "validated@example.test" not in caplog.text
    assert "loadx-system.vercel.app" not in caplog.text


def test_mailjet_reports_multiple_missing_fields_without_values(caplog):
    invalid = config(
        mailjet_api_key=None,
        mailjet_secret_key=None,
        mailjet_sender="not-an-address",
        password_recovery_url="http://bad.test/reset",
    )
    with pytest.raises(IdentityUnavailableError):
        MailjetRecoveryDelivery(invalid)
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "loadx.security"
    ]
    assert len(events) == 1
    assert events[0]["failed_checks"] == (
        "recovery_url_invalid,api_key_missing,secret_key_missing,sender_invalid"
    )
    assert "not-an-address" not in caplog.text
    assert "bad.test" not in caplog.text
