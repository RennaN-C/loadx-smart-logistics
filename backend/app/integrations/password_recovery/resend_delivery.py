"""HTTPS-only Resend adapter for transactional password recovery.

No SMTP port, user data or token is included in exception/log messages.
"""

import hashlib
import json
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.integrations.password_recovery.delivery import (
    RecoveryDeliveryFailure,
    valid_recovery_url,
)
from app.integrations.password_recovery.message import build_recovery_message
from app.modules.auth.totp import IdentityUnavailableError

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_EMAIL_ADDRESS = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+\Z"
)


class ResendRecoveryDelivery:
    """Resend REST API, using only an explicitly configured and owned sender."""

    def __init__(self, config: Settings) -> None:
        self.config = config
        valid_url = valid_recovery_url(config)
        sender = config.resend_sender or ""
        key = config.resend_api_key
        if (
            config.password_recovery_provider != "resend"
            or not valid_url
            or not key
            or not key.get_secret_value().startswith("re_")
            or not _EMAIL_ADDRESS.fullmatch(sender)
        ):
            raise IdentityUnavailableError
        if sender.lower() == "onboarding@resend.dev":
            permitted = (config.resend_test_recipient or "").strip()
            if not _EMAIL_ADDRESS.fullmatch(permitted):
                raise IdentityUnavailableError

    def deliver(self, email: str, token: str) -> None:
        """Send after the reset token is committed, with bounded HTTPS timeout."""
        key = self.config.resend_api_key
        sender = self.config.resend_sender
        url = self.config.password_recovery_url
        if key is None or sender is None or url is None:
            raise IdentityUnavailableError
        if sender.lower() == "onboarding@resend.dev":
            permitted = (self.config.resend_test_recipient or "").strip()
            if email.casefold() != permitted.casefold():
                raise RecoveryDeliveryFailure("recipient_not_allowed")
        message = build_recovery_message(email, token, sender, url)
        payload = {
            "from": str(message["From"]),
            "to": [email],
            "subject": str(message["Subject"]),
            "text": message.get_body(preferencelist=("plain",)).get_content(),
            "html": message.get_body(preferencelist=("html",)).get_content(),
        }
        request = Request(
            _RESEND_ENDPOINT,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key.get_secret_value()}",
                "Content-Type": "application/json",
                "Idempotency-Key": "loadx-recovery-"
                + hashlib.sha256(token.encode("utf-8")).hexdigest(),
            },
            method="POST",
        )
        # urlopen verifies the server certificate by default.
        # Only a closed set of error categories and numeric HTTP status escapes;
        # never propagate provider error bodies, URL or exception messages.
        try:
            with urlopen(request, timeout=5) as response:
                if not 200 <= response.status < 300:
                    status = response.status
                    safe_status = (
                        status
                        if isinstance(status, int) and 100 <= status <= 599
                        else None
                    )
                    raise RecoveryDeliveryFailure(
                        "http_rejection", http_status=safe_status
                    )
        except HTTPError as exc:
            status = exc.code
            safe_status = (
                status if isinstance(status, int) and 100 <= status <= 599 else None
            )
            raise RecoveryDeliveryFailure(
                "http_rejection", http_status=safe_status
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
            raise RecoveryDeliveryFailure(category) from None
