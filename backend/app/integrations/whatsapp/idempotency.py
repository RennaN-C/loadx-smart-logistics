"""Port de reserva de envio; implementação em memória exclusiva para doubles."""

import hashlib
import json
import uuid
from threading import Lock
from typing import TYPE_CHECKING, Protocol

from app.integrations.whatsapp.errors import WhatsAppErrorCode, WhatsAppProviderError

if TYPE_CHECKING:
    from app.integrations.whatsapp.provider import OutgoingWhatsAppMessage


class SendGuard(Protocol):
    def claim(
        self, operation_id: uuid.UUID, fingerprint: str
    ) -> "OutgoingWhatsAppMessage | None":
        """Reserve atomicamente; None autoriza um POST, receipt reutiliza sucesso.

        Rejeite fingerprint diferente e reserva ainda sem receipt. Persistência
        deve sobreviver a workers/restarts e confirmar a reserva antes do IO.
        """
        ...

    def complete(
        self, operation_id: uuid.UUID, receipt: "OutgoingWhatsAppMessage"
    ) -> None:
        """Confirme o receipt sem remover a reserva em caso de erro."""
        ...


def send_fingerprint(recipient_phone: str, content: str) -> str:
    data = json.dumps([recipient_phone, content], ensure_ascii=True).encode()
    return hashlib.sha256(data).hexdigest()


class InMemorySendGuard:
    """Double limitado, sem garantia entre processos; nunca compor saída real."""

    def __init__(self, *, capacity: int = 10_000) -> None:
        self._capacity = capacity
        self._lock = Lock()
        self._claims: dict[uuid.UUID, tuple[str, OutgoingWhatsAppMessage | None]] = {}

    def claim(
        self, operation_id: uuid.UUID, fingerprint: str
    ) -> "OutgoingWhatsAppMessage | None":
        with self._lock:
            if operation_id in self._claims:
                previous_fingerprint, receipt = self._claims[operation_id]
                if previous_fingerprint != fingerprint:
                    raise WhatsAppProviderError(WhatsAppErrorCode.IDENTITY_CONFLICT)
                if receipt is None:
                    raise WhatsAppProviderError(
                        WhatsAppErrorCode.SEND_IN_DOUBT, delivery_uncertain=True
                    )
                return receipt
            if len(self._claims) >= self._capacity:
                raise WhatsAppProviderError(WhatsAppErrorCode.IDEMPOTENCY_UNAVAILABLE)
            self._claims[operation_id] = (fingerprint, None)
            return None

    def complete(
        self, operation_id: uuid.UUID, receipt: "OutgoingWhatsAppMessage"
    ) -> None:
        with self._lock:
            fingerprint, _ = self._claims[operation_id]
            self._claims[operation_id] = (fingerprint, receipt)
