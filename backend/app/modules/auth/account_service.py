import logging
import uuid

from sqlalchemy.orm import Session

from app.core.security import verify_and_update_password
from app.core.security_events import SecurityEvent, emit_security_event
from app.modules.auth.schemas import OwnPasswordChange, OwnProfileUpdate, OwnSessionRead
from app.modules.auth.sessions import (
    AuthSessionInvalidError,
    AuthSessionService,
    ResolvedAuthSession,
)
from app.modules.auth.throttling import LoginThrottleService
from app.modules.users.models import User
from app.modules.users.schemas import UserUpdate
from app.modules.users.service import UserService


class OwnPasswordInvalidError(Exception):
    pass


class OwnSessionNotFoundError(Exception):
    pass


class AccountService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserService(db)
        self.sessions = AuthSessionService(db)
        self.throttle = LoginThrottleService(db)

    def _lock_account(self, current: ResolvedAuthSession) -> User:
        user = self.users.lock_account(current.user.id)
        session = self.sessions.repository.get_owned_for_update(
            current.auth_session.id, user.id
        )
        now = self.sessions.now_provider()
        if (
            not user.active
            or session is None
            or session.revoked_at is not None
            or self.sessions._is_expired(session, now)
        ):
            raise AuthSessionInvalidError
        return user

    def update_profile(
        self, current: ResolvedAuthSession, data: OwnProfileUpdate
    ) -> User:
        user = self._lock_account(current)
        result = self.users.update_user(
            user.id, UserUpdate(**data.model_dump()), actor_id=user.id
        )
        emit_security_event(SecurityEvent.OWN_PROFILE_UPDATED, user_id=str(user.id))
        return result

    def change_password(
        self, current: ResolvedAuthSession, data: OwnPasswordChange, client_ip: str
    ) -> None:
        self.throttle.ensure_login_allowed(current.user.email, client_ip)
        user = self._lock_account(current)
        valid, _ = verify_and_update_password(data.current_password, user.password_hash)
        if not valid:
            delay = self.throttle.record_failed_login(user.email, client_ip)
            emit_security_event(
                SecurityEvent.OWN_PASSWORD_REJECTED,
                level=logging.WARNING,
                user_id=str(user.id),
                alert=True,
                delay_seconds=delay,
            )
            raise OwnPasswordInvalidError
        # UserService stages password, audit and all-session revocation in one commit.
        self.users.update_user(
            user.id, UserUpdate(password=data.new_password), actor_id=user.id
        )
        emit_security_event(SecurityEvent.OWN_PASSWORD_CHANGED, user_id=str(user.id))

    def list_sessions(self, current: ResolvedAuthSession) -> list[OwnSessionRead]:
        sessions = self.sessions.repository.list_live_for_user(
            current.user.id, self.sessions.now_provider()
        )
        return [
            OwnSessionRead(
                id=item.id,
                created_at=item.created_at,
                last_seen_at=item.last_seen_at,
                idle_expires_at=item.idle_expires_at,
                absolute_expires_at=item.absolute_expires_at,
                current=item.id == current.auth_session.id,
            )
            for item in sessions
        ]

    def revoke_session(
        self, current: ResolvedAuthSession, session_id: uuid.UUID
    ) -> bool:
        self._lock_account(current)
        session = self.sessions.repository.get_owned_for_update(
            session_id, current.user.id
        )
        if session is None:
            raise OwnSessionNotFoundError
        if session.revoked_at is None:
            self.sessions.repository.revoke(session, self.sessions.now_provider())
        self.db.commit()
        emit_security_event(
            SecurityEvent.SESSION_REVOKED,
            user_id=str(current.user.id),
            session_id=str(session_id),
        )
        return session_id == current.auth_session.id

    def revoke_other_sessions(self, current: ResolvedAuthSession) -> None:
        self._lock_account(current)
        others = self.sessions.repository.list_active_for_user_for_update(
            current.user.id
        )
        now = self.sessions.now_provider()
        count = 0
        for session in others:
            if session.id != current.auth_session.id:
                self.sessions.repository.revoke(session, now)
                count += 1
        self.db.commit()
        emit_security_event(
            SecurityEvent.USER_SESSIONS_REVOKED,
            user_id=str(current.user.id),
            revoked_count=count,
        )
