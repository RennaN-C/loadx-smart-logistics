import logging
import uuid

from sqlalchemy.orm import Session

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_and_update_password,
)
from app.modules.auth.schemas import AuthLogin, TokenRead
from app.modules.auth.throttling import LoginThrottleService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserNotFoundError, UserService


class AuthInvalidCredentialsError(Exception):
    pass


class AuthInvalidTokenError(Exception):
    pass


class AuthInactiveUserError(Exception):
    pass


class AuthBootstrapAlreadyCompletedError(Exception):
    pass


logger = logging.getLogger(__name__)
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-account-password")


class AuthService:
    def __init__(self, db: Session) -> None:
        self.user_service = UserService(db)
        self.login_throttle = LoginThrottleService(db)

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

    def login(self, data: AuthLogin, client_ip: str = "unknown") -> TokenRead:
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
        logger.info("Authentication succeeded: user_id=%s", user.id)

        access_token = create_access_token(
            str(user.id),
            {
                "email": user.email,
                "role": user.role,
            },
        )
        return TokenRead(access_token=access_token)

    def _reject_failed_login(
        self,
        email: str,
        client_ip: str,
        *,
        known_account: bool,
        privileged_account: bool = False,
    ) -> None:
        delay_seconds = self.login_throttle.record_failed_login(email, client_ip)
        logger.warning(
            "Authentication failed: known_account=%s privileged_account=%s "
            "delay_seconds=%d",
            known_account,
            privileged_account,
            delay_seconds,
        )

    def get_current_user_from_token(self, token: str) -> User:
        try:
            payload = decode_access_token(token)
            subject = payload.get("sub")
            if not isinstance(subject, str):
                raise AuthInvalidTokenError
            user_id = uuid.UUID(subject)
            user = self.user_service.get_user(user_id)
        except (InvalidTokenError, ValueError, UserNotFoundError) as exc:
            raise AuthInvalidTokenError from exc

        if not user.active:
            raise AuthInactiveUserError
        return user
