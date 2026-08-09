from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.core.responses import error_response, openapi_error_responses
from app.modules.auth.dependencies import get_auth_service, get_current_user
from app.modules.auth.schemas import AuthLogin, TokenRead
from app.modules.auth.service import (
    AuthInvalidCredentialsError,
    AuthService,
)
from app.modules.auth.throttling import AuthRateLimitedError
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenRead,
    responses=openapi_error_responses(401, 422, 429),
)
def login(
    request: Request,
    data: AuthLogin,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenRead | JSONResponse:
    try:
        client_ip = request.client.host if request.client is not None else "unknown"
        return service.login(data, client_ip)
    except AuthInvalidCredentialsError:
        return error_response(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_CREDENTIALS",
            "E-mail ou senha inválidos.",
        )
    except AuthRateLimitedError as error:
        return error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "AUTH_RATE_LIMITED",
            "Muitas tentativas de login. Tente novamente mais tarde.",
            headers={"Retry-After": str(error.retry_after_seconds)},
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
