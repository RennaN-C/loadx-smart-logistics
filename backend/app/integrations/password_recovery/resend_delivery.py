"""HTTPS-only Resend adapter for transactional password recovery.

No SMTP port, user data or token is included in exception/log messages.
"""

import hashlib
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.core.config import Settings
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
        raw_url = config.password_recovery_url or ""
        try:
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

    def deliver(self, email: str, token: str) -> None:
        """Send after the reset token is committed, with bounded HTTPS timeout."""
        key = self.config.resend_api_key
        sender = self.config.resend_sender
        url = self.config.password_recovery_url
        if key is None or sender is None or url is None:
            raise IdentityUnavailableError
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
        # urlopen verifies the server certificate by default. Never log its
        # exception, which could include private response headers or body.
        with urlopen(request, timeout=5) as response:
            if not 200 <= response.status < 300:
                raise OSError("Recovery provider rejected the request")
