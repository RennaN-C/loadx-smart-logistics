"""Sensitive persistence owned by auth; callers first lock the account."""

import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.modules.auth.models import (
    AuthChallenge,
    AuthFactor,
    AuthPasswordReset,
    AuthRecoveryCode,
)


class IdentityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, entity):
        self.db.add(entity)
        self.db.flush()
        return entity

    def factor(self, user_id: uuid.UUID) -> AuthFactor:
        factor = self.db.scalar(
            select(AuthFactor)
            .where(AuthFactor.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return factor if factor is not None else self.add(AuthFactor(user_id=user_id))

    def find_factor(
        self, user_id: uuid.UUID, *, for_update: bool = False
    ) -> AuthFactor | None:
        statement = select(AuthFactor).where(AuthFactor.user_id == user_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.db.scalar(statement)

    def challenge_user(self, digest: str) -> uuid.UUID | None:
        return self.db.scalar(
            select(AuthChallenge.user_id).where(AuthChallenge.token_hash == digest)
        )

    def challenge(self, digest: str) -> AuthChallenge | None:
        return self.db.scalar(
            select(AuthChallenge)
            .where(AuthChallenge.token_hash == digest)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def reset_user(self, digest: str) -> uuid.UUID | None:
        return self.db.scalar(
            select(AuthPasswordReset.user_id).where(
                AuthPasswordReset.token_hash == digest
            )
        )

    def reset(self, digest: str) -> AuthPasswordReset | None:
        return self.db.scalar(
            select(AuthPasswordReset)
            .where(AuthPasswordReset.token_hash == digest)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def invalidate_resets(self, user_id: uuid.UUID, now: datetime) -> None:
        self.db.execute(
            update(AuthPasswordReset)
            .where(
                AuthPasswordReset.user_id == user_id,
                AuthPasswordReset.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )

    def invalidate_challenges(self, user_id: uuid.UUID, now: datetime) -> None:
        self.db.execute(
            update(AuthChallenge)
            .where(
                AuthChallenge.user_id == user_id, AuthChallenge.consumed_at.is_(None)
            )
            .values(consumed_at=now)
        )
        self.db.execute(
            update(AuthFactor)
            .where(AuthFactor.user_id == user_id)
            .values(security_version=AuthFactor.security_version + 1)
        )

    def recovery(self, user_id: uuid.UUID, digest: str) -> AuthRecoveryCode | None:
        return self.db.scalar(
            select(AuthRecoveryCode)
            .where(
                AuthRecoveryCode.user_id == user_id,
                AuthRecoveryCode.code_hash == digest,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def replace_codes(self, user_id: uuid.UUID, digests: list[str]) -> None:
        self.db.execute(
            delete(AuthRecoveryCode).where(AuthRecoveryCode.user_id == user_id)
        )
        for digest in digests:
            self.add(AuthRecoveryCode(user_id=user_id, code_hash=digest))
