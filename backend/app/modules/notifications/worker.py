"""Separate durable worker. Run: python -m app.modules.notifications.worker."""

import logging
import signal
import threading
from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.integrations.outbox import MockOutboxTransport, OutboxTransport
from app.modules.notifications.outbox_service import OutboxService, deliver

logger = logging.getLogger("loadx.outbox")


def process_one(
    factory: Callable[[], Session],
    transport: OutboxTransport,
    *,
    lease_seconds: int = 60,
    max_attempts: int = 5,
    base_seconds: int = 30,
    cap_seconds: int = 3600,
) -> bool:
    with factory() as db, db.begin():
        claim = OutboxService(db).claim(lease_seconds)
    if claim is None:
        return False
    # No open Session, row lock or business transaction during transport I/O.
    status, code = deliver(transport, claim)
    with factory() as db, db.begin():
        accepted = OutboxService(db).complete(
            claim,
            status,
            code,
            max_attempts=max_attempts,
            base_seconds=base_seconds,
            cap_seconds=cap_seconds,
        )
    logger.info(
        "outbox_result event_id=%s generation=%s status=%s accepted=%s",
        claim.event_id,
        claim.generation,
        status,
        accepted,
    )
    return True


def main() -> None:
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _signum, _frame: stop.set())
    engine = create_engine(
        settings.database_url,
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c statement_timeout=5000 -c lock_timeout=2000",
        },
    )
    factory = sessionmaker(bind=engine, autoflush=False)
    transport = MockOutboxTransport()
    logging.basicConfig(level=logging.INFO)
    try:
        while not stop.is_set():
            try:
                processed = process_one(
                    factory,
                    transport,
                    lease_seconds=settings.outbox_lease_seconds,
                    max_attempts=settings.outbox_max_attempts,
                    base_seconds=settings.outbox_base_seconds,
                    cap_seconds=settings.outbox_cap_seconds,
                )
                if not processed:
                    stop.wait(settings.outbox_poll_seconds)
            # Keep the loop alive without exposing exception text or credentials.
            except Exception:  # noqa: BLE001
                logger.warning(
                    "outbox_cycle_failed reason=DATABASE_OR_PROCESSING_FAILED"
                )
                stop.wait(settings.outbox_poll_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
