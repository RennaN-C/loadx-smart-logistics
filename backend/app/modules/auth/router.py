from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.schemas import AuthLogin, TokenRead
from app.modules.auth.service import (
    AuthInactiveUserError,
    AuthInvalidCredentialsError,
    AuthInvalidTokenError,
    AuthService,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserRead
from app.modules.users.service import UserEmailAlreadyExistsError

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    return AuthService(db)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(409, 422),
)
def register_user(
    data: UserCreate,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User | JSONResponse:
    try:
        return service.register_user(data)
    except UserEmailAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "USER_EMAIL_ALREADY_EXISTS",
            "Já existe um usuário cadastrado com este e-mail.",
            [{"field": "email"}],
        )


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
    service: Annotated[AuthService, Depends(get_auth_service)],
    authorization: Annotated[str | None, Header()] = None,
) -> User | JSONResponse:
    try:
        return service.get_current_user_from_authorization(authorization)
    except AuthInvalidTokenError:
        return error_response(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_TOKEN",
            "Token ausente ou inválido.",
        )
    except AuthInactiveUserError:
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "AUTH_USER_INACTIVE",
            "Usuário inativo.",
        )
