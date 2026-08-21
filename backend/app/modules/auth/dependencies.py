from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.core.http_security import UNSAFE_HTTP_METHODS
from app.database.session import get_db
from app.modules.auth.service import AuthService
from app.modules.auth.sessions import (
    AuthSessionInactiveUserError,
    AuthSessionInvalidError,
    AuthSessionService,
    ResolvedAuthSession,
)
from app.modules.users.models import User
from app.modules.users.schemas import USER_ROLE_VALUES

CSRF_HEADER_NAME = "X-CSRF-Token"
session_cookie_scheme = APIKeyCookie(
    name=settings.session_cookie_name,
    scheme_name="SessionCookie",
    auto_error=False,
)


def get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    return AuthService(db)


def get_auth_session_service(
    db: Annotated[Session, Depends(get_db)],
) -> AuthSessionService:
    return AuthSessionService(db)


def get_current_session(
    request: Request,
    session_token: Annotated[str | None, Depends(session_cookie_scheme)],
    service: Annotated[AuthSessionService, Depends(get_auth_session_service)],
) -> ResolvedAuthSession:
    if session_token is None:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_TOKEN",
            "Sessão ausente ou inválida.",
        )

    try:
        resolved_session = service.resolve_session(session_token)
    except AuthSessionInvalidError:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_TOKEN",
            "Sessão ausente ou inválida.",
        ) from None
    except AuthSessionInactiveUserError:
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "AUTH_USER_INACTIVE",
            "Usuário inativo.",
        ) from None

    csrf_token = request.headers.get(CSRF_HEADER_NAME)
    if request.method in UNSAFE_HTTP_METHODS and (
        csrf_token is None or not service.validate_csrf_token(session_token, csrf_token)
    ):
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "AUTH_CSRF_INVALID",
            "Token CSRF ausente ou inválido.",
        )
    return resolved_session


def get_current_user(
    current_session: Annotated[ResolvedAuthSession, Depends(get_current_session)],
) -> User:
    return current_session.user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    roles = frozenset(allowed_roles)
    invalid_roles = roles.difference(USER_ROLE_VALUES)
    if not roles or invalid_roles:
        invalid_values = ", ".join(sorted(invalid_roles))
        message = "At least one valid role is required"
        if invalid_values:
            message = f"Invalid roles: {invalid_values}"
        raise ValueError(message)

    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise ApiError(
                status.HTTP_403_FORBIDDEN,
                "AUTH_FORBIDDEN",
                "Usuário sem permissão para esta ação.",
            )
        return current_user

    return role_dependency
