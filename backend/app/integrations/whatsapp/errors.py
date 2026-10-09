"""Erros fechados do canal, sem payload ou mensagem de exceção externa."""

from enum import StrEnum


class WhatsAppErrorCode(StrEnum):
    NOT_CONFIGURED = "WHATSAPP_NOT_CONFIGURED"
    INVALID_MESSAGE = "WHATSAPP_INVALID_MESSAGE"
    AUTHENTICATION_FAILED = "WHATSAPP_AUTHENTICATION_FAILED"
    REJECTED = "WHATSAPP_REJECTED"
    RATE_LIMITED = "WHATSAPP_RATE_LIMITED"
    UNAVAILABLE = "WHATSAPP_UNAVAILABLE"
    TIMEOUT = "WHATSAPP_TIMEOUT"
    INVALID_RESPONSE = "WHATSAPP_INVALID_RESPONSE"
    IDEMPOTENCY_UNAVAILABLE = "WHATSAPP_IDEMPOTENCY_UNAVAILABLE"
    IDENTITY_CONFLICT = "WHATSAPP_IDENTITY_CONFLICT"
    SEND_IN_DOUBT = "WHATSAPP_SEND_IN_DOUBT"
    INCOMING_UNSUPPORTED = "WHATSAPP_INCOMING_UNSUPPORTED"


class WhatsAppProviderError(Exception):
    def __init__(
        self,
        code: WhatsAppErrorCode,
        *,
        delivery_uncertain: bool = False,
    ) -> None:
        self.code = code
        self.delivery_uncertain = delivery_uncertain
        super().__init__(code.value)
