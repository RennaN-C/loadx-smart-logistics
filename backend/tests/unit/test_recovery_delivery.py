import pytest

from app.core.config import Settings
from app.integrations.password_recovery.delivery import (
    SmtpRecoveryDelivery,
    dispatch_recovery,
)
from app.modules.auth.totp import IdentityUnavailableError


def config(**overrides):
    return Settings(
        app_env="local",
        password_recovery_provider="smtp",
        password_recovery_url="https://example.test/password-reset",
        smtp_host="smtp.example.test",
        smtp_username="local-test",
        smtp_password="fictitious-only",
        smtp_sender="loadx@example.test",
        _env_file=None,
        **overrides,
    )


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
