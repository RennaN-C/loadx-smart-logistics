from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.core.responses import error_response, openapi_error_responses
from app.modules.auth.dependencies import get_auth_service, get_current_user
from app.modules.auth.schemas import AuthLogin, TokenRead
from app.modules.auth.service import (
    AuthInactiveUserError,
    AuthInvalidCredentialsError,
    AuthService,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenRead,
    responses=openapi_error_responses(401, 403, 422),
)
def login(
    data: AuthLogin,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenRead | JSONResponse:
    try:
        return service.login(data)
    except AuthInvalidCredentialsError:
        return error_response(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_CREDENTIALS",
            "E-mail ou senha inválidos.",
        )
    except AuthInactiveUserError:
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "AUTH_USER_INACTIVE",
            "Usuário inativo.",
        )


@router.get(
    "/me",
    response_model=UserRead,
    responses=openapi_error_responses(401, 403, 422),
)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user
