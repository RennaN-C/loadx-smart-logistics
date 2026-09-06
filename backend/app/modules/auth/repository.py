import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import AuthLoginThrottle, AuthSession
from app.modules.users.models import User


class AuthLoginThrottleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_update(
        self,
        scope: str,
        subject_hash: str,
    ) -> AuthLoginThrottle | None:
        statement = (
            select(AuthLoginThrottle)
            .where(
                AuthLoginThrottle.scope == scope,
                AuthLoginThrottle.subject_hash == subject_hash,
            )
            .with_for_update()
        )
        return self.db.scalar(statement)

    def add(self, throttle: AuthLoginThrottle) -> AuthLoginThrottle:
        self.db.add(throttle)
        self.db.flush()
        return throttle

    def delete(self, throttle: AuthLoginThrottle) -> None:
        self.db.delete(throttle)


class AuthSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, auth_session: AuthSession) -> AuthSession:
        self.db.add(auth_session)
        self.db.flush()
        return auth_session

    def get_with_user_for_update(
        self,
        token_hash: str,
    ) -> tuple[AuthSession, User] | None:
        statement = (
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(AuthSession.token_hash == token_hash)
            .with_for_update()
        )
        row = self.db.execute(statement).one_or_none()
        return (row[0], row[1]) if row is not None else None

    def get_for_update(self, token_hash: str) -> AuthSession | None:
        statement = (
            select(AuthSession)
            .where(AuthSession.token_hash == token_hash)
            .with_for_update()
        )
        return self.db.scalar(statement)

    def list_active_for_user_for_update(
        self,
        user_id: uuid.UUID,
    ) -> Sequence[AuthSession]:
        statement = (
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .order_by(AuthSession.id)
            .with_for_update()
        )
        return self.db.scalars(statement).all()

    def revoke(self, auth_session: AuthSession, revoked_at: datetime) -> None:
        auth_session.revoked_at = revoked_at
        self.db.add(auth_session)
