"""Proposta de adapter Meta Cloud API: somente envio, sem ações de domínio."""

import logging
import re
import time
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx2

from app.core.observability import OperationalEvent, emit_operational_event
from app.integrations.whatsapp.errors import WhatsAppErrorCode, WhatsAppProviderError
from app.integrations.whatsapp.http_logging import sensitive_http_send
from app.integrations.whatsapp.idempotency import SendGuard, send_fingerprint
from app.integrations.whatsapp.provider import (
    IncomingWhatsAppMessage,
    OutgoingWhatsAppMessage,
)
from app.shared.validators import normalize_phone

if TYPE_CHECKING:
    from app.core.config import Settings


class MetaWhatsAppProvider:
    def __init__(
        self,
        configured: "Settings",
        *,
        transport: httpx2.BaseTransport | None = None,
        send_guard: SendGuard | None = None,
    ) -> None:
        token = configured.whatsapp_access_token.get_secret_value()
        if (
            not configured.whatsapp_real_enabled
            or not token
            or re.search(r"[^\x21-\x7e]", token)
            or re.fullmatch(
                r"\d{1,32}", configured.whatsapp_phone_number_id, flags=re.ASCII
            )
            is None
            or re.fullmatch(
                r"v\d{1,3}\.\d{1,2}", configured.whatsapp_api_version, flags=re.ASCII
            )
            is None
            or (
                configured.whatsapp_country_code
                and re.fullmatch(
                    r"[1-9]\d{0,2}", configured.whatsapp_country_code, flags=re.ASCII
                )
                is None
            )
        ):
            raise WhatsAppProviderError(WhatsAppErrorCode.NOT_CONFIGURED)
        self._token = configured.whatsapp_access_token
        self._url = (
            f"https://graph.facebook.com/{configured.whatsapp_api_version}/"
            f"{configured.whatsapp_phone_number_id}/messages"
        )
        self._country_code = configured.whatsapp_country_code
        self._timeout = configured.whatsapp_timeout_seconds
        self._max_attempts = configured.whatsapp_max_attempts
        self._backoff = configured.whatsapp_retry_backoff_seconds
        self._transport = transport
        self._send_guard = send_guard

    def receive_message(
        self, message: IncomingWhatsAppMessage
    ) -> IncomingWhatsAppMessage:
        raise WhatsAppProviderError(WhatsAppErrorCode.INCOMING_UNSUPPORTED)

    def send_response(
        self, message: OutgoingWhatsAppMessage
    ) -> OutgoingWhatsAppMessage:
        try:
            return self._send_response(message)
        except WhatsAppProviderError as error:
            emit_operational_event(
                OperationalEvent.WHATSAPP_SEND_FAILED,
                level=logging.WARNING,
                alert=True,
                reason=error.code.value,
            )
            raise

    def _send_response(
        self, message: OutgoingWhatsAppMessage
    ) -> OutgoingWhatsAppMessage:
        phone = self._validate_message(message)
        previous = self._claim(message, phone)
        if previous is not None:
            return previous

        response = self._post_message(phone, message.content)
        self._raise_for_status(response)
        message_id = self._message_id(response)
        receipt = replace(
            message, provider_message_id=message_id, accepted_at=datetime.now(UTC)
        )
        self._complete(message, receipt)
        emit_operational_event(
            OperationalEvent.WHATSAPP_SEND_ACCEPTED,
            operation_id=str(message.operation_id) if message.operation_id else None,
        )
        return receipt

    def _guard(self) -> SendGuard:
        if self._send_guard is None:
            raise WhatsAppProviderError(WhatsAppErrorCode.IDEMPOTENCY_UNAVAILABLE)
        return self._send_guard

    def _claim(
        self, message: OutgoingWhatsAppMessage, phone: str
    ) -> OutgoingWhatsAppMessage | None:
        if message.operation_id is None:
            return None
        guard = self._guard()
        try:
            return guard.claim(
                message.operation_id, send_fingerprint(phone, message.content)
            )
        except WhatsAppProviderError:
            raise
        except Exception:  # noqa: BLE001 - storage details are not part of the port
            raise WhatsAppProviderError(
                WhatsAppErrorCode.IDEMPOTENCY_UNAVAILABLE
            ) from None

    def _complete(
        self, message: OutgoingWhatsAppMessage, receipt: OutgoingWhatsAppMessage
    ) -> None:
        if message.operation_id is None:
            return
        try:
            self._guard().complete(message.operation_id, receipt)
        except Exception:  # noqa: BLE001 - accepted send cannot be retried blindly
            raise WhatsAppProviderError(
                WhatsAppErrorCode.SEND_IN_DOUBT, delivery_uncertain=True
            ) from None

    def _raise_for_status(self, response: httpx2.Response) -> None:
        if response.status_code in {401, 403}:
            raise WhatsAppProviderError(WhatsAppErrorCode.AUTHENTICATION_FAILED)
        if response.status_code == 429:
            raise WhatsAppProviderError(WhatsAppErrorCode.RATE_LIMITED)
        if response.status_code == 408 or response.status_code >= 500:
            raise WhatsAppProviderError(
                WhatsAppErrorCode.UNAVAILABLE, delivery_uncertain=True
            )
        if 400 <= response.status_code < 500:
            error_code = self._error_code(response)
            if error_code == 190:
                raise WhatsAppProviderError(WhatsAppErrorCode.AUTHENTICATION_FAILED)
            if error_code in {4, 80007, 130429, 131048, 131056}:
                raise WhatsAppProviderError(WhatsAppErrorCode.RATE_LIMITED)
        if response.status_code != 200:
            raise WhatsAppProviderError(WhatsAppErrorCode.REJECTED)

    def _validate_message(self, message: OutgoingWhatsAppMessage) -> str:
        if (
            not isinstance(message.recipient_phone, str)
            or not isinstance(message.content, str)
            or not message.content.strip()
            or len(message.content) > 4096
            or (
                message.operation_id is not None
                and not isinstance(message.operation_id, uuid.UUID)
            )
        ):
            raise WhatsAppProviderError(WhatsAppErrorCode.INVALID_MESSAGE)
        phone = message.recipient_phone.strip()
        if phone.startswith("+"):
            if re.fullmatch(r"\+[1-9]\d{6,14}", phone, flags=re.ASCII) is None:
                raise WhatsAppProviderError(WhatsAppErrorCode.INVALID_MESSAGE)
            return phone[1:]
        if not self._country_code:
            raise WhatsAppProviderError(WhatsAppErrorCode.INVALID_MESSAGE)
        try:
            normalized = normalize_phone(phone)
        except ValueError:
            raise WhatsAppProviderError(WhatsAppErrorCode.INVALID_MESSAGE) from None
        if not normalized:
            raise WhatsAppProviderError(WhatsAppErrorCode.INVALID_MESSAGE)
        return self._country_code + normalized

    def _post_message(self, phone: str, content: str) -> httpx2.Response:
        with (
            sensitive_http_send(),
            httpx2.Client(transport=self._transport, trust_env=False) as client,
        ):
            for attempt in range(1, self._max_attempts + 1):
                try:
                    return client.post(
                        self._url,
                        headers={
                            "Authorization": f"Bearer {self._token.get_secret_value()}",
                            "Accept": "application/json",
                        },
                        json={
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": phone,
                            "type": "text",
                            "text": {"preview_url": False, "body": content},
                        },
                        timeout=httpx2.Timeout(self._timeout),
                        follow_redirects=False,
                    )
                except (
                    httpx2.ConnectTimeout,
                    httpx2.PoolTimeout,
                    httpx2.ConnectError,
                ) as error:
                    if attempt == self._max_attempts:
                        code = (
                            WhatsAppErrorCode.TIMEOUT
                            if isinstance(error, httpx2.TimeoutException)
                            else WhatsAppErrorCode.UNAVAILABLE
                        )
                        raise WhatsAppProviderError(code) from None
                    emit_operational_event(
                        OperationalEvent.WHATSAPP_SEND_RETRY,
                        attempt=attempt,
                        reason="CONNECTION_NOT_ESTABLISHED",
                    )
                    time.sleep(self._backoff * 2 ** (attempt - 1))
                except httpx2.TimeoutException:
                    raise WhatsAppProviderError(
                        WhatsAppErrorCode.TIMEOUT, delivery_uncertain=True
                    ) from None
                except httpx2.RequestError:
                    raise WhatsAppProviderError(
                        WhatsAppErrorCode.UNAVAILABLE, delivery_uncertain=True
                    ) from None
        raise WhatsAppProviderError(WhatsAppErrorCode.UNAVAILABLE)

    @staticmethod
    def _error_code(response: httpx2.Response) -> int | None:
        """Lê somente código numérico; textos/trace_ids externos não atravessam a port."""
        try:
            code = response.json()["error"]["code"]
        except (ValueError, KeyError, TypeError):
            return None
        return code if type(code) is int else None

    @staticmethod
    def _message_id(response: httpx2.Response) -> str:
        try:
            payload = response.json()
            messages = payload["messages"]
            message_id = messages[0]["id"]
            valid = (
                payload.get("messaging_product") == "whatsapp"
                and isinstance(messages, list)
                and len(messages) == 1
                and isinstance(message_id, str)
                and re.fullmatch(r"wamid\.[A-Za-z0-9_+/=-]{1,249}", message_id)
                is not None
            )
        except (
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
        ):
            valid = False
        if not valid:
            raise WhatsAppProviderError(
                WhatsAppErrorCode.INVALID_RESPONSE, delivery_uncertain=True
            ) from None
        return message_id
