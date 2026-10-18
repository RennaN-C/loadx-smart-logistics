import pytest

from app.core.config import Settings
from app.integrations.password_recovery.delivery import (
    SmtpRecoveryDelivery,
    dispatch_recovery,
)
from app.modules.auth.totp import IdentityUnavailableError


def config(**overrides):
    values = {
        "app_env": "local",
        "password_recovery_provider": "smtp",
        "password_recovery_url": "https://example.test/password-reset",
        "smtp_host": "smtp.example.test",
        "smtp_username": "local-test",
        "smtp_password": "fictitious-only",
        "smtp_sender": "loadx@example.test",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_smtp_uses_verified_tls_timeout_and_fragment(monkeypatch):
    captured = {}

    class FakeSmtp:
        def __init__(self, host, port, **kwargs):
            captured.update(host=host, port=port, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self, user, password):
            captured["login"] = (user, password)

        def send_message(self, message):
            captured["message"] = message

    monkeypatch.setattr(
        "app.integrations.password_recovery.delivery.smtplib.SMTP_SSL", FakeSmtp
    )
    SmtpRecoveryDelivery(config()).deliver("person@example.test", "random-test-token")
    assert captured["context"].check_hostname
    assert captured["timeout"] == 5
    assert captured["port"] == 465
    assert "#token=random-test-token" in captured["message"].get_content()
    assert "fictitious-only" not in captured["message"].get_content()


@pytest.mark.parametrize(
    "url",
    [
        "http://example.test/password-reset",
        "https://u:p@example.test/reset",
        "https://example.test/reset?token=x",
        "https://example.test/reset#x",
    ],
)
def test_unapproved_recovery_url_fails_closed(url):
    settings = config()
    settings.password_recovery_url = url
    with pytest.raises(IdentityUnavailableError):
        SmtpRecoveryDelivery(settings)


def test_delivery_failure_is_sanitized(caplog):
    class Failing:
        def deliver(self, email, token):
            raise OSError("private smtp detail and token")

    dispatch_recovery(Failing(), "private@example.test", "private-test-token")
    assert "AUTH_RECOVERY_DELIVERY_FAILED" in caplog.text
    assert "private" not in caplog.text


@pytest.mark.parametrize("security", ["starttls", "local"])
def test_explicit_transport_order(monkeypatch, security):
    calls = []

    class FakeSmtp:
        def __init__(self, host, port, **kwargs):
            assert kwargs == {"timeout": 5}
            calls.append("connect")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            calls.append("ehlo")

        def starttls(self, *, context):
            assert context.check_hostname
            assert context.verify_mode == 2
            calls.append("tls")

        def login(self, *args):
            calls.append("login")

        def send_message(self, message):
            calls.append("send")

    monkeypatch.setattr(
        "app.integrations.password_recovery.delivery.smtplib.SMTP", FakeSmtp
    )
    kwargs = {"smtp_security": security, "smtp_port": 587}
    if security == "local":
        kwargs.update(
            smtp_host="localhost",
            smtp_username=None,
            smtp_password=None,
            password_recovery_url="http://localhost:5173/password-reset",
            smtp_port=1025,
        )
    SmtpRecoveryDelivery(config(**kwargs)).deliver("person@example.test", "token")
    assert calls == (
        ["connect", "ehlo", "tls", "ehlo", "login", "send"]
        if security == "starttls"
        else ["connect", "send"]
    )


def test_starttls_failure_never_authenticates_or_sends(monkeypatch, caplog):
    import smtplib

    class NoTls:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            pass

        def starttls(self, **kwargs):
            raise smtplib.SMTPNotSupportedError("private server response")

        def login(self, *args):
            pytest.fail("Credentials must not be sent without TLS")

        def send_message(self, *args):
            pytest.fail("Message must not be sent without TLS")

    monkeypatch.setattr(
        "app.integrations.password_recovery.delivery.smtplib.SMTP", NoTls
    )
    dispatch_recovery(
        SmtpRecoveryDelivery(config(smtp_security="starttls")),
        "private@example.test",
        "private-token",
    )
    assert "AUTH_RECOVERY_DELIVERY_FAILED" in caplog.text
    assert "private" not in caplog.text


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:5173.evil.test/password-reset",
        "http://localhost:5173/password-reset?next=https://evil.test",
        "http://127.0.0.1:5173/password-reset",
        "http://localhost:5174/password-reset",
        "http://localhost:5173/other",
        "https://example.test:bad/reset",
        "https://example.test/reset\n",
        "https://example.test\\@evil.test/reset",
    ],
)
def test_url_validation_is_strict(url):
    settings = config(password_recovery_url=url)
    with pytest.raises(IdentityUnavailableError):
        SmtpRecoveryDelivery(settings)


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "app_env": "production",
            "secret_key": "test-only-production-secret-32-characters",
            "smtp_security": "local",
        },
        {"smtp_security": "local"},
        {"smtp_security": "local", "smtp_username": None, "smtp_password": None},
        {
            "smtp_host": "localhost",
            "smtp_security": "local",
            "smtp_username": "user",
            "smtp_password": None,
        },
        {
            "app_env": "production",
            "secret_key": "test-only-production-secret-32-characters",
            "password_recovery_url": "http://localhost:5173/password-reset",
        },
    ],
)
def test_insecure_transport_configuration_fails_closed(overrides):
    settings = config(**overrides)
    with pytest.raises(IdentityUnavailableError):
        SmtpRecoveryDelivery(settings)
