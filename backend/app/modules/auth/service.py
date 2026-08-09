import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_and_update_password,
)
from app.core.security_events import SecurityEvent, emit_security_event
from app.modules.auth.schemas import AuthLogin
from app.modules.auth.sessions import AuthSessionService, IssuedAuthSession
from app.modules.auth.throttling import LoginThrottleService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService


class AuthInvalidCredentialsError(Exception):
    pass


class AuthBootstrapAlreadyCompletedError(Exception):
    pass


_DUMMY_PASSWORD_HASH = hash_password("not-a-real-account-password")


@dataclass(frozen=True)
class LoginResult:
    user: User
    session: IssuedAuthSession


class AuthService:
    def __init__(self, db: Session) -> None:
        self.user_service = UserService(db)
        self.login_throttle = LoginThrottleService(db)
        self.auth_sessions = AuthSessionService(db)

    def bootstrap_first_admin(self, name: str, email: str, password: str) -> User:
        if self.user_service.has_users():
            raise AuthBootstrapAlreadyCompletedError

        return self.user_service.create_user(
            UserCreate(
                name=name,
                email=email,
                password=password,
                role="ADMIN",
                active=True,
            )
        )

    def login(self, data: AuthLogin, client_ip: str = "unknown") -> LoginResult:
        self.login_throttle.ensure_login_allowed(data.email, client_ip)
        user = self.user_service.get_user_by_email(data.email)
        if user is None:
            verify_and_update_password(data.password, _DUMMY_PASSWORD_HASH)
            self._reject_failed_login(data.email, client_ip, known_account=False)
            raise AuthInvalidCredentialsError
        password_verified, updated_hash = verify_and_update_password(
            data.password,
            user.password_hash,
        )
        if not password_verified:
            self._reject_failed_login(
                data.email,
                client_ip,
                known_account=True,
                privileged_account=user.role in {"ADMIN", "LOGISTICS_MANAGER"},
            )
            raise AuthInvalidCredentialsError
        if not user.active:
            self._reject_failed_login(
                data.email,
                client_ip,
                known_account=True,
                privileged_account=user.role in {"ADMIN", "LOGISTICS_MANAGER"},
            )
            raise AuthInvalidCredentialsError
        if updated_hash is not None:
            user = self.user_service.upgrade_password_hash(user, updated_hash)
        self.login_throttle.reset_after_success(data.email, client_ip)
        emit_security_event(
            SecurityEvent.LOGIN_SUCCEEDED,
            user_id=str(user.id),
            role=user.role,
            privileged_account=user.role in {"ADMIN", "LOGISTICS_MANAGER"},
        )
        issued_session = self.auth_sessions.create_session(user.id)
        return LoginResult(
            user=user,
            session=issued_session,
        )

    def _reject_failed_login(
        self,
        email: str,
        client_ip: str,
        *,
        known_account: bool,
        privileged_account: bool = False,
    ) -> None:
        delay_seconds = self.login_throttle.record_failed_login(email, client_ip)
        emit_security_event(
            SecurityEvent.LOGIN_FAILED,
            level=logging.WARNING,
            alert=privileged_account or delay_seconds > 0,
            known_account=known_account,
            privileged_account=privileged_account,
            delay_seconds=delay_seconds,
        )
