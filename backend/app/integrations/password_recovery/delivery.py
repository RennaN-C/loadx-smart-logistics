"""Real SMTP port; a fake is injected only by tests."""

import logging
import smtplib
import ssl
from typing import Literal, Protocol
from urllib.parse import urlsplit

from app.core.config import Settings, settings
from app.core.security_events import SecurityEvent, emit_security_event
from app.integrations.password_recovery.message import build_recovery_message
from app.modules.auth.totp import IdentityUnavailableError


class RecoveryDelivery(Protocol):
    def deliver(self, email: str, token: str) -> None: ...

class RecoveryDeliveryFailure(OSError):
    """Safe, allowlisted diagnostics without provider response content."""

    def __init__(
        self,
        category: Literal[
            "http_rejection", "timeout", "tls", "network", "recipient_not_allowed"
        ],
        http_status: int | None = None,
    ) -> None:
        super().__init__("Recovery delivery failed")
        self.category = category
        self.http_status = http_status




def valid_recovery_url(config: Settings) -> bool:
    """Validate the recovery URL uniformly for all external delivery providers."""
    try:
        raw_url = config.password_recovery_url or ""
        url = urlsplit(raw_url)
        local_url = (
            config.app_env == "local"
            and raw_url == "http://localhost:5173/password-reset"
        )
        return (
            bool(url.hostname)
            and (url.scheme == "https" or local_url)
            and not any((url.username, url.password, url.query, url.fragment))
            and not any(char.isspace() or ord(char) < 32 for char in raw_url)
            and "\\" not in raw_url
            and url.port != 0
        )
    except ValueError:
        return False


class SmtpRecoveryDelivery:
    def __init__(self, config: Settings) -> None:
        self.config = config
        valid_url = valid_recovery_url(config)
        local_transport = config.smtp_security == "local"
        if (
            config.password_recovery_provider != "smtp"
            or not config.smtp_host
            or not config.smtp_sender
            or not valid_url
            or (
                local_transport
                and (
                    config.app_env != "local"
                    or config.smtp_host
                    not in {"localhost", "127.0.0.1", "::1", "mailpit"}
                    or config.smtp_username
                    or config.smtp_password
                )
            )
            or (
                not local_transport
                and (not config.smtp_username or not config.smtp_password)
            )
        ):
            raise IdentityUnavailableError
        if any(
            "\r" in value or "\n" in value
            for value in (
                config.smtp_sender,
                config.smtp_username or "",
                config.smtp_host,
            )
        ):
            raise IdentityUnavailableError

    def deliver(self, email: str, token: str) -> None:
        message = build_recovery_message(
            email, token, self.config.smtp_sender, self.config.password_recovery_url
        )
        tls_context = ssl.create_default_context()
        tls_context.verify_mode = ssl.CERT_REQUIRED
        tls_context.check_hostname = True
        tls_context.minimum_version = ssl.TLSVersion.TLSv1_2
        transport = (
            smtplib.SMTP_SSL if self.config.smtp_security == "ssl" else smtplib.SMTP
        )
        options = {"timeout": 5}
        if self.config.smtp_security == "ssl":
            options["context"] = tls_context
        with transport(self.config.smtp_host, self.config.smtp_port, **options) as smtp:
            if self.config.smtp_security == "starttls":
                smtp.ehlo()
                # Never fall back to plaintext if STARTTLS is missing or fails.
                smtp.starttls(context=tls_context)
                smtp.ehlo()
            if self.config.smtp_security != "local":
                smtp.login(
                    self.config.smtp_username,
                    self.config.smtp_password.get_secret_value(),
                )
            smtp.send_message(message)


def get_recovery_delivery() -> RecoveryDelivery:
    if settings.password_recovery_provider == "resend":
        from app.integrations.password_recovery.resend_delivery import (
            ResendRecoveryDelivery,
        )

        return ResendRecoveryDelivery(settings)
    return SmtpRecoveryDelivery(settings)


def dispatch_recovery(delivery: RecoveryDelivery, email: str, token: str) -> None:
    try:
        delivery.deliver(email, token)
    except RecoveryDeliveryFailure as exc:
        # Only fixed categories and numeric HTTP status; never log exceptions,
        # recipient, token, request headers, response body or remote URL.
        details: dict[str, str | int | bool] = {
            "delivery_provider": "resend",
            "failure_category": exc.category,
        }
        if exc.http_status is not None:
            details["provider_http_status"] = exc.http_status
        emit_security_event(
            SecurityEvent.RECOVERY_DELIVERY_FAILED,
            level=logging.ERROR,
            alert=True,
            **details,
        )
    except OSError:
        # Preserve the generic SMTP behavior without leaking provider replies.
        emit_security_event(
            SecurityEvent.RECOVERY_DELIVERY_FAILED, level=logging.ERROR, alert=True
        )
