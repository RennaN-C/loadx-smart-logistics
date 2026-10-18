import uuid
from collections.abc import Callable
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.account_service import (
    AccountService,
    OwnPasswordInvalidError,
    OwnSessionNotFoundError,
)
from app.modules.auth.dependencies import (
    CSRF_HEADER_NAME,
    get_auth_service,
    get_current_session,
    get_current_user,
)
from app.modules.auth.identity_service import MfaChallengeResult
from app.modules.auth.schemas import (
    AuthLogin,
    MfaChallengeRead,
    OwnPasswordChange,
    OwnProfileUpdate,
    OwnSessionRead,
)
from app.modules.auth.service import (
    AuthInvalidCredentialsError,
    AuthService,
)
from app.modules.auth.sessions import AuthSessionInvalidError, ResolvedAuthSession
from app.modules.auth.throttling import AuthRateLimitedError
from app.modules.auth.totp import IdentityUnavailableError
from app.modules.users.models import User
from app.modules.users.schemas import UserRead
from app.modules.users.service import UserEmailAlreadyExistsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=UserRead | MfaChallengeRead,
    responses=openapi_error_responses(401, 403, 422, 429, 503),
)
def login(
    request: Request,
    response: Response,
    data: AuthLogin,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User | MfaChallengeRead | JSONResponse:
    try:
        client_ip = request.client.host if request.client is not None else "unknown"
        result = service.login(data, client_ip)
        if isinstance(result, MfaChallengeResult):
            clear_session_cookie(response)
            return MfaChallengeRead(**result.__dict__)
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
        from app.modules.access_profiles.service import ProfileService

        ProfileService(service.user_service.db).resolve(result.user)
        return result.user
    except IdentityUnavailableError:
        return error_response(
            503,
            "AUTH_IDENTITY_UNAVAILABLE",
            "Autenticação indisponível. Contate o suporte.",
        )
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
    current_user: Annotated[User, Depends(get_current_user)],
    current_session: Annotated[ResolvedAuthSession, Depends(get_current_session)],
) -> User:
    response.headers[CSRF_HEADER_NAME] = current_session.csrf_token
    return current_user


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


def get_account_service(db: Annotated[Session, Depends(get_db)]) -> AccountService:
    return AccountService(db)


T = TypeVar("T")


def account_operation(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except IdentityUnavailableError:
        raise ApiError(
            503,
            "AUTH_IDENTITY_UNAVAILABLE",
            "Serviço de identidade indisponível. Contate o suporte.",
        ) from None
    except AuthSessionInvalidError:
        raise ApiError(
            401, "AUTH_INVALID_TOKEN", "Sessão ausente ou inválida."
        ) from None
    except OwnPasswordInvalidError:
        raise ApiError(
            400, "AUTH_CURRENT_PASSWORD_INVALID", "Senha atual incorreta."
        ) from None
    except UserEmailAlreadyExistsError:
        raise ApiError(
            409, "USER_EMAIL_ALREADY_EXISTS", "E-mail já cadastrado."
        ) from None
    except OwnSessionNotFoundError:
        raise ApiError(
            404, "AUTH_SESSION_NOT_FOUND", "Sessão não encontrada."
        ) from None
    except AuthRateLimitedError as error:
        raise ApiError(
            429,
            "AUTH_RATE_LIMITED",
            "Muitas tentativas. Tente novamente mais tarde.",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from None


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.patch(
    "/me",
    response_model=UserRead,
    responses=openapi_error_responses(400, 401, 403, 409, 422, 429, 503),
)
def update_me(
    request: Request,
    data: OwnProfileUpdate,
    current: Annotated[ResolvedAuthSession, Depends(get_current_session)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> User:
    return account_operation(
        lambda: service.update_profile(
            current,
            data,
            client_ip=request.client.host if request.client else "unknown",
        )
    )


@router.post(
    "/me/password",
    status_code=204,
    responses=openapi_error_responses(400, 401, 403, 422, 429),
)
def change_own_password(
    request: Request,
    response: Response,
    data: OwnPasswordChange,
    current: Annotated[ResolvedAuthSession, Depends(get_current_session)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    account_operation(lambda: service.change_password(current, data, client_ip))
    clear_session_cookie(response)


@router.get("/me/sessions", responses=openapi_error_responses(401, 403, 422))
def list_own_sessions(
    current: Annotated[ResolvedAuthSession, Depends(get_current_session)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> list[OwnSessionRead]:
    return service.list_sessions(current)


@router.delete(
    "/me/sessions/{session_id}",
    status_code=204,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def revoke_own_session(
    session_id: uuid.UUID,
    response: Response,
    current: Annotated[ResolvedAuthSession, Depends(get_current_session)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> None:
    if account_operation(lambda: service.revoke_session(current, session_id)):
        clear_session_cookie(response)


@router.post(
    "/me/sessions/revoke-others",
    status_code=204,
    responses=openapi_error_responses(401, 403, 422),
)
def revoke_other_sessions(
    current: Annotated[ResolvedAuthSession, Depends(get_current_session)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> None:
    account_operation(lambda: service.revoke_other_sessions(current))
