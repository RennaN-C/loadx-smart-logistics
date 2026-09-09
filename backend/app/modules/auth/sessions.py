import base64
import hashlib
import hmac
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security_events import SecurityEvent, emit_security_event
from app.modules.auth.models import AuthSession
from app.modules.auth.repository import AuthSessionRepository
from app.modules.users.models import User

SESSION_TOKEN_BYTES = 32
SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
SESSION_ABSOLUTE_TIMEOUT = timedelta(hours=8)


class AuthSessionInvalidError(Exception):
    pass


class AuthSessionInactiveUserError(Exception):
    pass


@dataclass(frozen=True)
class IssuedAuthSession:
    token: str
    csrf_token: str
    auth_session: AuthSession


@dataclass(frozen=True)
class ResolvedAuthSession:
    token: str
    csrf_token: str
    auth_session: AuthSession
    user: User


class AuthSessionService:
    def __init__(
        self,
        db: Session,
        *,
        secret_key: str = settings.secret_key,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.db = db
        self.repository = AuthSessionRepository(db)
        self.secret_key = secret_key.encode()
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def create_session(self, user_id: uuid.UUID) -> IssuedAuthSession:
        now = self.now_provider()
        token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        auth_session = self.repository.add(
            AuthSession(
                user_id=user_id,
                token_hash=self.hash_token(token),
                created_at=now,
                last_seen_at=now,
                idle_expires_at=now + SESSION_IDLE_TIMEOUT,
                absolute_expires_at=now + SESSION_ABSOLUTE_TIMEOUT,
            )
        )
        self.db.commit()
        self.db.refresh(auth_session)
        emit_security_event(
            SecurityEvent.SESSION_CREATED,
            session_id=str(auth_session.id),
            user_id=str(user_id),
        )
        return IssuedAuthSession(
            token=token,
            csrf_token=self.csrf_token_for(token),
            auth_session=auth_session,
        )

    def resolve_session(self, token: str) -> ResolvedAuthSession:
        now = self.now_provider()
        result = self.repository.get_with_user_for_update(self.hash_token(token))
        if result is None:
            raise AuthSessionInvalidError

        auth_session, user = result
        if auth_session.revoked_at is not None or self._is_expired(auth_session, now):
            if auth_session.revoked_at is None:
                self.repository.revoke(auth_session, now)
                self.db.commit()
                emit_security_event(
                    SecurityEvent.SESSION_EXPIRED,
                    session_id=str(auth_session.id),
                    user_id=str(auth_session.user_id),
                )
            raise AuthSessionInvalidError
        if not user.active:
            self.revoke_all_for_user(user.id)
            raise AuthSessionInactiveUserError

        auth_session.last_seen_at = now
        auth_session.idle_expires_at = min(
            now + SESSION_IDLE_TIMEOUT,
            self._as_utc(auth_session.absolute_expires_at),
        )
        self.db.add(auth_session)
        self.db.commit()
        self.db.refresh(auth_session)
        return ResolvedAuthSession(
            token=token,
            csrf_token=self.csrf_token_for(token),
            auth_session=auth_session,
            user=user,
        )

    def revoke_session(self, token: str) -> None:
        auth_session = self.repository.get_for_update(self.hash_token(token))
        if auth_session is not None and auth_session.revoked_at is None:
            self.repository.revoke(auth_session, self.now_provider())
        self.db.commit()
        if auth_session is not None:
            emit_security_event(
                SecurityEvent.SESSION_REVOKED,
                session_id=str(auth_session.id),
                user_id=str(auth_session.user_id),
            )

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        revoked_count = self.stage_revoke_all_for_user(user_id)
        self.db.commit()
        emit_security_event(
            SecurityEvent.USER_SESSIONS_REVOKED,
            user_id=str(user_id),
            revoked_count=revoked_count,
        )
        return revoked_count

    def stage_revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        active_sessions = self.repository.list_active_for_user_for_update(user_id)
        revoked_at = self.now_provider()
        for auth_session in active_sessions:
            self.repository.revoke(auth_session, revoked_at)
        return len(active_sessions)

    def validate_csrf_token(self, token: str, csrf_token: str) -> bool:
        return hmac.compare_digest(self.csrf_token_for(token), csrf_token)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def csrf_token_for(self, token: str) -> str:
        digest = hmac.new(
            self.secret_key,
            f"csrf:{token}".encode(),
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def _is_expired(self, auth_session: AuthSession, now: datetime) -> bool:
        return now >= min(
            self._as_utc(auth_session.idle_expires_at),
            self._as_utc(auth_session.absolute_expires_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
