"""Controlled HTTP emitter composition. No Meta adapter or media ingestion."""

from dataclasses import dataclass, field

import anyio
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.integrations.external_commands import (
    BoundExternalActorResolver,
    HmacExternalAuthenticator,
    TrustedIntegration,
)
from app.modules.external_commands.service import ExternalCommandService

INBOUND_INTEGRATION_ID = "loadx-controlled-webhook"
MAX_IN_FLIGHT = 4
BODY_TIMEOUT_SECONDS = 5


@dataclass
class InboundWebhookRuntime:
    commands: ExternalCommandService
    limiter: anyio.CapacityLimiter = field(
        default_factory=lambda: anyio.CapacityLimiter(MAX_IN_FLIGHT)
    )
    engine: Engine | None = field(default=None, repr=False)


def build_inbound_webhook(settings: Settings) -> InboundWebhookRuntime | None:
    if not settings.inbound_webhook_enabled:
        return None
    # Settings rejects enabled configurations without this exclusive key.
    assert settings.inbound_webhook_signing_key is not None
    authenticator = HmacExternalAuthenticator(
        TrustedIntegration(
            INBOUND_INTEGRATION_ID, frozenset(settings.inbound_webhook_capabilities)
        ),
        settings.inbound_webhook_signing_key,
    )
    resolver = BoundExternalActorResolver(
        {
            (INBOUND_INTEGRATION_ID, subject): actor_id
            for subject, actor_id in settings.inbound_webhook_bindings.items()
        }
    )
    engine = create_engine(
        settings.database_url,
        pool_size=MAX_IN_FLIGHT,
        max_overflow=0,
        pool_timeout=2,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 2,
            "options": "-c statement_timeout=5000 -c lock_timeout=2000",
        },
    )
    return InboundWebhookRuntime(
        ExternalCommandService(
            sessionmaker(bind=engine, autoflush=False), authenticator, resolver
        ),
        engine=engine,
    )
