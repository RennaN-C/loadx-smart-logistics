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
        try:
            raw_url = config.password_recovery_url or ""
            url = urlsplit(raw_url)
            local_url = (
                config.app_env == "local"
                and raw_url == "http://localhost:5173/password-reset"
            )
            valid_url = (
                bool(url.hostname)
                and (url.scheme == "https" or local_url)
                and not any((url.username, url.password, url.query, url.fragment))
                and not any(char.isspace() or ord(char) < 32 for char in raw_url)
                and "\\" not in raw_url
                and url.port != 0
            )
        except ValueError:
            raise IdentityUnavailableError from None
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
    return SmtpRecoveryDelivery(settings)


def dispatch_recovery(delivery: RecoveryDelivery, email: str, token: str) -> None:
    try:
        delivery.deliver(email, token)
    except OSError:
        # Do not include SMTP responses, destination, token, or exception payload.
        emit_security_event(
            SecurityEvent.RECOVERY_DELIVERY_FAILED, level=logging.ERROR, alert=True
        )
