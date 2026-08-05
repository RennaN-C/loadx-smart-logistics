import uuid

from sqlalchemy.orm import Session

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    verify_password,
)
from app.modules.auth.schemas import AuthLogin, TokenRead
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


class AuthService:
    def __init__(self, db: Session) -> None:
        self.user_service = UserService(db)

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

    def login(self, data: AuthLogin) -> TokenRead:
        user = self.user_service.get_user_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise AuthInvalidCredentialsError
        if not user.active:
            raise AuthInactiveUserError

        access_token = create_access_token(
            str(user.id),
            {
                "email": user.email,
                "role": user.role,
            },
        )
        return TokenRead(access_token=access_token)

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
