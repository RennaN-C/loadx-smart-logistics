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

    def lock_session_user(self, user_id: uuid.UUID) -> User | None:
        return self.db.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def add(self, auth_session: AuthSession) -> AuthSession:
        self.db.add(auth_session)
        self.db.flush()
        return auth_session

    def get_with_user_for_update(
        self,
        token_hash: str,
    ) -> tuple[AuthSession, User] | None:
        user_id = self.db.scalar(
            select(AuthSession.user_id).where(AuthSession.token_hash == token_hash)
        )
        if user_id is None:
            return None
        # Same user -> sessions lock order as password changes and revocation.
        user = self.lock_session_user(user_id)
        auth_session = self.get_for_update(token_hash)
        if user is None or auth_session is None:
            return None
        return auth_session, user

    def get_for_update(self, token_hash: str) -> AuthSession | None:
        statement = (
            select(AuthSession)
            .where(AuthSession.token_hash == token_hash)
            .with_for_update()
            .execution_options(populate_existing=True)
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

    def list_live_for_user(
        self, user_id: uuid.UUID, now: datetime
    ) -> Sequence[AuthSession]:
        return self.db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.idle_expires_at > now,
                AuthSession.absolute_expires_at > now,
            )
            .order_by(AuthSession.created_at.desc(), AuthSession.id)
        ).all()

    def get_owned_for_update(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> AuthSession | None:
        return self.db.scalar(
            select(AuthSession)
            .where(AuthSession.id == session_id, AuthSession.user_id == user_id)
            .with_for_update()
        )

    def revoke(self, auth_session: AuthSession, revoked_at: datetime) -> None:
        auth_session.revoked_at = revoked_at
        self.db.add(auth_session)
