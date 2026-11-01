"""Non-persistent concurrency guard; no domain writes or arbitrary SQL."""

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session


class AssistantConcurrencyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def try_acquire(self, actor: str) -> bool:
        key = int.from_bytes(
            hashlib.sha256(("loadx-assistant:" + actor).encode()).digest()[:8],
            signed=True,
        )
        return bool(
            self.db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key})
        )
