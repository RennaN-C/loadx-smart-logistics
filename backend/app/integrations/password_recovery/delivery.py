"""Real SMTP port; a fake is injected only by tests."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import urlsplit

from app.core.config import Settings, settings
from app.core.security_events import SecurityEvent, emit_security_event
from app.modules.auth.totp import IdentityUnavailableError


class RecoveryDelivery(Protocol):
    def deliver(self, email: str, token: str) -> None: ...


class SmtpRecoveryDelivery:
    def __init__(self, config: Settings) -> None:
        self.config = config
        url = urlsplit(config.password_recovery_url or "")
        if (
            config.password_recovery_provider != "smtp"
            or not config.smtp_host
            or not config.smtp_username
            or not config.smtp_password
            or not config.smtp_sender
            or url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise IdentityUnavailableError
        if any(
            "\r" in value or "\n" in value
            for value in (config.smtp_sender, config.smtp_username)
        ):
            raise IdentityUnavailableError

    def deliver(self, email: str, token: str) -> None:
        message = EmailMessage()
        message["Subject"] = "LoadX — recuperação de acesso"
        message["From"] = self.config.smtp_sender
        message["To"] = email
        message.set_content(
            "Uma recuperação de senha foi solicitada. O link expira em 15 minutos. Se não foi você, ignore esta mensagem.\n\n"
            + str(self.config.password_recovery_url)
            + "#token="
            + token
        )
        with smtplib.SMTP_SSL(
            self.config.smtp_host,
            self.config.smtp_port,
            timeout=5,
            context=ssl.create_default_context(),
        ) as smtp:
            smtp.login(
                self.config.smtp_username, self.config.smtp_password.get_secret_value()
            )
            smtp.send_message(message)


def get_recovery_delivery() -> RecoveryDelivery:
    return SmtpRecoveryDelivery(settings)


def dispatch_recovery(delivery: RecoveryDelivery, email: str, token: str) -> None:
    try:
        delivery.deliver(email, token)
    except (OSError, smtplib.SMTPException):
        # Do not include SMTP responses, destination, token, or exception payload.
        emit_security_event(
            SecurityEvent.RECOVERY_DELIVERY_FAILED, level=logging.ERROR, alert=True
        )
