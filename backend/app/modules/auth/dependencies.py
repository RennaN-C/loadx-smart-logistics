from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.database.session import get_db
from app.modules.auth.service import (
    AuthInactiveUserError,
    AuthInvalidTokenError,
    AuthService,
)
from app.modules.users.models import User
from app.modules.users.schemas import USER_ROLE_VALUES

bearer_scheme = HTTPBearer(scheme_name="BearerAuth", auto_error=False)


def get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    return AuthService(db)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_TOKEN",
            "Token ausente ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return service.get_current_user_from_token(credentials.credentials)
    except AuthInvalidTokenError:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_TOKEN",
            "Token ausente ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except AuthInactiveUserError:
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "AUTH_USER_INACTIVE",
            "Usuário inativo.",
        ) from None


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
