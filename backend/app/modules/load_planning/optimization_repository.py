"""PostgreSQL transaction-scoped request exclusion, with no committed pending job."""

import hashlib
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.load_planning.distribution_models import OptimizationRequest


class OptimizationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def try_lock(self, actor: uuid.UUID, key: uuid.UUID) -> bool:
        digest = hashlib.sha256(b"optimize:v1:" + actor.bytes + key.bytes).digest()
        lock_id = int.from_bytes(digest[:8], byteorder="big", signed=True)
        return bool(self.db.scalar(select(func.pg_try_advisory_xact_lock(lock_id))))

    def get(self, actor: uuid.UUID, key: uuid.UUID) -> OptimizationRequest | None:
        return self.db.get(OptimizationRequest, (actor, key))

    def add(self, request: OptimizationRequest) -> None:
        self.db.add(request)
