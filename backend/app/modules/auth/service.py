import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_and_update_password,
)
from app.core.security_events import SecurityEvent, emit_security_event
from app.modules.auth.schemas import AuthLogin
from app.modules.auth.sessions import (
    AuthSessionInvalidError,
    AuthSessionService,
    AuthTrustedDeviceRequiredError,
    IssuedAuthSession,
)
from app.modules.auth.throttling import LoginThrottleService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService

if TYPE_CHECKING:
    from app.modules.auth.identity_service import MfaChallengeResult


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

    def login(
        self,
        data: AuthLogin,
        client_ip: str = "unknown",
        *,
        trusted_device_token: str | None = None,
    ) -> "LoginResult | MfaChallengeResult":
        # Local import preserves public auth/users service boundaries without cycles.
        from app.modules.auth.identity_service import MfaChallengeResult

        self.login_throttle.ensure_login_allowed(data.email, client_ip)
        user = self.user_service.get_user_by_email(data.email)
        if user is None:
            verify_and_update_password(data.password, _DUMMY_PASSWORD_HASH)
            self._reject_failed_login(data.email, client_ip, known_account=False)
            raise AuthInvalidCredentialsError
        expected_hash = user.password_hash
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
        user = self.user_service.lock_account(user.id)
        if not user.active or user.password_hash != expected_hash:
            raise AuthInvalidCredentialsError
        if updated_hash is not None:
            user = self.user_service.upgrade_password_hash(user, updated_hash)
        verified_hash = updated_hash or expected_hash
        result = self._issue_verified_login(
            user, verified_hash, data.email, client_ip, trusted_device_token
        )
        if isinstance(result, MfaChallengeResult):
            return result
        issued_session = result
        emit_security_event(
            SecurityEvent.LOGIN_SUCCEEDED,
            user_id=str(user.id),
            role=user.role,
            privileged_account=user.role in {"ADMIN", "LOGISTICS_MANAGER"},
        )
        return LoginResult(
            user=user,
            session=issued_session,
        )

    def _issue_verified_login(
        self,
        user: User,
        verified_hash: str,
        email: str,
        client_ip: str,
        trusted_device_token: str | None,
    ) -> "IssuedAuthSession | MfaChallengeResult":
        from app.modules.auth.identity_service import IdentityService

        identity = IdentityService(self.auth_sessions.db)
        if identity.required(user):
            from app.modules.auth.totp import cipher

            cipher(identity.key)
            try:
                issued_session = self.auth_sessions.create_session(
                    user.id,
                    expected_password_hash=verified_hash,
                    password_only=True,
                    trusted_device_token=trusted_device_token,
                )
            except AuthTrustedDeviceRequiredError:
                return identity.begin(user, expected_hash=verified_hash)
            except AuthSessionInvalidError:
                raise AuthInvalidCredentialsError from None
            self.login_throttle.reset_after_success(email, client_ip)
        else:
            self.login_throttle.reset_after_success(email, client_ip)
            try:
                issued_session = self.auth_sessions.create_session(
                    user.id, expected_password_hash=verified_hash, password_only=True
                )
            except AuthSessionInvalidError:
                raise AuthInvalidCredentialsError from None
        return issued_session

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
