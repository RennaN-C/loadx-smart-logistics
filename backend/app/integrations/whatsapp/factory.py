"""Seleção explícita do provider; não ativa fornecedor ou cria conta externa."""

from functools import lru_cache

import httpx2

from app.core.config import Settings, settings
from app.integrations.whatsapp.idempotency import SendGuard
from app.integrations.whatsapp.meta import MetaWhatsAppProvider
from app.integrations.whatsapp.provider import WhatsAppProvider, mock_whatsapp_provider


def create_whatsapp_provider(
    configured: Settings,
    *,
    transport: httpx2.BaseTransport | None = None,
    send_guard: SendGuard | None = None,
) -> WhatsAppProvider:
    if configured.whatsapp_provider == "mock":
        return mock_whatsapp_provider
    return MetaWhatsAppProvider(configured, transport=transport, send_guard=send_guard)


@lru_cache(maxsize=1)
def get_configured_whatsapp_provider() -> WhatsAppProvider:
    return create_whatsapp_provider(settings)
