import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate
from app.modules.users.service import (
    UserEmailAlreadyExistsError,
    UserNotFoundError,
    UserService,
)

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Annotated[Session, Depends(get_db)]) -> UserService:
    return UserService(db)


def error_response(status_code: int, code: str, message: str, details: list[Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or [],
        },
    )


@router.get("", response_model=list[UserRead])
def list_users(service: Annotated[UserService, Depends(get_user_service)]) -> list[User]:
    return list(service.list_users())


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> User | JSONResponse:
    try:
        return service.create_user(data)
    except UserEmailAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "USER_EMAIL_ALREADY_EXISTS",
            "Já existe um usuário cadastrado com este e-mail.",
            [{"field": "email"}],
        )


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: uuid.UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> User | JSONResponse:
    try:
        return service.get_user(user_id)
    except UserNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "USER_NOT_FOUND",
            "Usuário não encontrado.",
            [{"field": "id"}],
        )


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> User | JSONResponse:
    try:
        return service.update_user(user_id, data)
    except UserNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "USER_NOT_FOUND",
            "Usuário não encontrado.",
            [{"field": "id"}],
        )
    except UserEmailAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "USER_EMAIL_ALREADY_EXISTS",
            "Já existe um usuário cadastrado com este e-mail.",
            [{"field": "email"}],
        )
