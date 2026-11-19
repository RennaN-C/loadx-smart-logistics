"""Session-scoped exclusion for long CPU-only calculations.

Transaction-scoped locks held the PostgreSQL transaction open for minutes,
causing connections to expire under idle-in-transaction settings. Advisory
session locks survive COMMIT but must always be explicitly released.
"""

import hashlib
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import func, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.modules.load_planning.distribution_models import OptimizationRequest


class OptimizationRepository:
    def __init__(self, db: Session, organization_id: uuid.UUID) -> None:
        self.db = db
        self.organization_id = organization_id

    @contextmanager
    def session_lock(self, actor: uuid.UUID, key: uuid.UUID) -> Iterator[bool]:
        """Exclude concurrent requests without holding a database transaction.

        The reserved connection has an advisory *session* lock, and its
        acquisition transaction is committed before the CPU-intensive work.
        Explicit unlock runs even after failure; invalidation closes a broken
        connection to prevent leaked session locks in the connection pool.
        """
        digest = hashlib.sha256(
            b"optimize:v2:" + self.organization_id.bytes + actor.bytes + key.bytes
        ).digest()
        lock_id = int.from_bytes(digest[:8], byteorder="big", signed=True)
        bind = self.db.get_bind()
        engine = bind.engine if isinstance(bind, Connection) else bind
        with engine.connect() as connection:
            acquired = False
            try:
                acquired = bool(
                    connection.scalar(select(func.pg_try_advisory_lock(lock_id)))
                )
                connection.commit()
                yield acquired
            finally:
                if acquired:
                    try:
                        connection.scalar(select(func.pg_advisory_unlock(lock_id)))
                        connection.commit()
                    except Exception:
                        connection.invalidate()
                        raise

    def get(self, actor: uuid.UUID, key: uuid.UUID) -> OptimizationRequest | None:
        return self.db.get(OptimizationRequest, (self.organization_id, actor, key))

    def add(self, request: OptimizationRequest) -> None:
        if request.organization_id != self.organization_id:
            raise ValueError("Optimization request belongs to a different organization")
        self.db.add(request)
