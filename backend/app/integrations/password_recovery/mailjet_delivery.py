"""Mailjet v3.1 transactional password recovery over HTTPS only.

Never put secrets, reset tokens, provider response bodies or addresses in logs.
"""

import base64
import json
import logging
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.core.security_events import SecurityEvent, emit_security_event
from app.integrations.password_recovery.delivery import (
    RecoveryDeliveryFailure,
    valid_recovery_url,
)
from app.integrations.password_recovery.message import build_recovery_message
from app.modules.auth.totp import IdentityUnavailableError

_MAILJET_ENDPOINT = "https://api.mailjet.com/v3.1/send"
_EMAIL_ADDRESS = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class MailjetRecoveryDelivery:
    """Single-recipient delivery using the verified sender for this API key."""

    def __init__(self, config: Settings) -> None:
        self.config = config
        # Only fixed diagnostic codes. Never log sender, secrets or recovery URL.
        failed_checks = [
            name
            for name, invalid in (
                ("provider_mismatch", config.password_recovery_provider != "mailjet"),
                ("recovery_url_invalid", not valid_recovery_url(config)),
                (
                    "api_key_missing",
                    config.mailjet_api_key is None
                    or not config.mailjet_api_key.get_secret_value(),
                ),
                (
                    "secret_key_missing",
                    config.mailjet_secret_key is None
                    or not config.mailjet_secret_key.get_secret_value(),
                ),
                (
                    "sender_invalid",
                    not _EMAIL_ADDRESS.fullmatch(config.mailjet_sender or ""),
                ),
            )
            if invalid
        ]
        if failed_checks:
            emit_security_event(
                SecurityEvent.RECOVERY_CONFIG_INVALID,
                level=logging.ERROR,
                alert=True,
                delivery_provider="mailjet",
                failed_checks=",".join(failed_checks),
            )
            raise IdentityUnavailableError

    def deliver(self, email: str, token: str) -> None:
        """Submit one message; do not treat a per-message rejection as success."""
        key = self.config.mailjet_api_key
        secret = self.config.mailjet_secret_key
        sender = self.config.mailjet_sender
        url = self.config.password_recovery_url
        if key is None or secret is None or sender is None or url is None:
            raise IdentityUnavailableError

        message = build_recovery_message(email, token, sender, url)
        payload = {
            "Messages": [
                {
                    "From": {"Email": sender, "Name": "LoadX | Segurança"},
                    "To": [{"Email": email}],
                    "Subject": str(message["Subject"]),
                    "TextPart": message.get_body(
                        preferencelist=("plain",)
                    ).get_content(),
                    "HTMLPart": message.get_body(
                        preferencelist=("html",)
                    ).get_content(),
                }
            ]
        }
        auth = base64.b64encode(
            (key.get_secret_value() + ":" + secret.get_secret_value()).encode("utf-8")
        ).decode("ascii")
        request = Request(
            _MAILJET_ENDPOINT,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": "Basic " + auth,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        # Certificate verification is enforced by urlopen. Never propagate raw
        # exceptions, response bodies or request headers into application logs.
        try:
            with urlopen(request, timeout=5) as response:
                status = response.status
                if not 200 <= status < 300:
                    raise RecoveryDeliveryFailure(
                        "http_rejection",
                        http_status=(
                            status
                            if isinstance(status, int) and 100 <= status <= 599
                            else None
                        ),
                        provider="mailjet",
                    )
                raw = response.read(16385)
                if len(raw) > 16384:
                    raise RecoveryDeliveryFailure(
                        "provider_rejected", provider="mailjet"
                    )
                try:
                    result = json.loads(raw)
                    messages = result["Messages"]
                    accepted = (
                        isinstance(messages, list)
                        and len(messages) == 1
                        and isinstance(messages[0], dict)
                        and messages[0].get("Status") == "success"
                    )
                except (ValueError, TypeError, KeyError, IndexError):
                    accepted = False
                if not accepted:
                    raise RecoveryDeliveryFailure(
                        "provider_rejected", provider="mailjet"
                    )
        except HTTPError as exc:
            status = exc.code
            raise RecoveryDeliveryFailure(
                "http_rejection",
                http_status=(
                    status if isinstance(status, int) and 100 <= status <= 599 else None
                ),
                provider="mailjet",
            ) from None
        except RecoveryDeliveryFailure:
            raise
        except OSError as exc:
            reason = exc.reason if isinstance(exc, URLError) else exc
            if isinstance(reason, TimeoutError):
                category = "timeout"
            elif isinstance(reason, ssl.SSLError):
                category = "tls"
            else:
                category = "network"
            raise RecoveryDeliveryFailure(category, provider="mailjet") from None
