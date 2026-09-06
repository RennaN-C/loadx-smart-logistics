from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.responses import error_response, openapi_error_responses
from app.modules.auth.dependencies import (
    CSRF_HEADER_NAME,
    get_auth_service,
    get_current_session,
)
from app.modules.auth.schemas import AuthLogin
from app.modules.auth.service import (
    AuthInvalidCredentialsError,
    AuthService,
)
from app.modules.auth.sessions import ResolvedAuthSession
from app.modules.auth.throttling import AuthRateLimitedError
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=UserRead,
    responses=openapi_error_responses(401, 403, 422, 429),
)
def login(
    request: Request,
    response: Response,
    data: AuthLogin,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User | JSONResponse:
    try:
        client_ip = request.client.host if request.client is not None else "unknown"
        result = service.login(data, client_ip)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=result.session.token,
            max_age=8 * 60 * 60,
            path="/",
            secure=settings.session_cookie_secure,
            httponly=True,
            samesite="lax",
        )
        response.headers[CSRF_HEADER_NAME] = result.session.csrf_token
        return result.user
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
    response: Response,
    current_session: Annotated[ResolvedAuthSession, Depends(get_current_session)],
) -> User:
    response.headers[CSRF_HEADER_NAME] = current_session.csrf_token
    return current_session.user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=openapi_error_responses(401, 403, 422),
)
def logout(
    response: Response,
    current_session: Annotated[ResolvedAuthSession, Depends(get_current_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    service.auth_sessions.revoke_session(current_session.token)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
