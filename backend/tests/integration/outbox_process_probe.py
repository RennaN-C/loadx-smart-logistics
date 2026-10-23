"""Isolated test subprocess. Only approved mock transport; never a real provider."""

import json
import os
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.integrations.outbox import MockOutboxTransport, TransientDeliveryError
from app.modules.notifications.outbox_service import OutboxService
from app.modules.notifications.worker import process_one


def main() -> None:
    url = os.environ["OUTBOX_TEST_DATABASE_URL"]
    if make_url(url).database != "loadx_test":
        raise RuntimeError("Probe requires exclusive loadx_test database")
    mode = sys.argv[1]
    engine = create_engine(url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, autoflush=False)
    if mode == "crash":
        with factory() as db, db.begin():
            claim = OutboxService(db).claim(60)
            assert claim is not None
        # Genuine process exit after the durable claim, before transport/completion.
        os._exit(73)
    if len(sys.argv) == 4:
        ready, start = map(Path, sys.argv[2:])
        ready.touch()
        deadline = time.monotonic() + 20
        while not start.exists():
            if time.monotonic() > deadline:
                raise RuntimeError("Probe start barrier timed out")
            time.sleep(0.01)
    calls = 0

    class Transport:
        def send(self, envelope):
            nonlocal calls
            calls += 1
            if mode == "transient":
                raise TransientDeliveryError("fixture-only-sensitive-marker")
            if mode == "timeout":
                raise TimeoutError("fixture-only-sensitive-marker")
            if mode != "mock":
                raise AssertionError("Unsupported test mode")
            MockOutboxTransport().send(envelope)

    progressed = process_one(factory, Transport(), base_seconds=30, cap_seconds=40)
    engine.dispose()
    print(json.dumps({"progressed": progressed, "calls": calls}), flush=True)


if __name__ == "__main__":
    main()
