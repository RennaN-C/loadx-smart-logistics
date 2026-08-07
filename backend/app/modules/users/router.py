import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserListRead, UserRead, UserUpdate
from app.modules.users.service import (
    UserEmailAlreadyExistsError,
    UserLastActiveAdminRequiredError,
    UserNotFoundError,
    UserService,
)

router = APIRouter(prefix="/users", tags=["users"])
AdminUser = Annotated[User, Depends(require_roles("ADMIN"))]


def get_user_service(db: Annotated[Session, Depends(get_db)]) -> UserService:
    return UserService(db)


@router.get(
    "",
    response_model=PageResponse[UserListRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_users(
    pagination: Pagination,
    _current_admin: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
) -> PageResponse[UserListRead]:
    result = service.list_users(pagination)
    return to_page_response(
        result,
        (UserListRead.model_validate(user) for user in result.items),
    )


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 409, 422),
)
def create_user(
    data: UserCreate,
    _current_admin: AdminUser,
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


@router.get(
    "/{user_id}",
    response_model=UserRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_user(
    user_id: uuid.UUID,
    _current_admin: AdminUser,
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


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    _current_admin: AdminUser,
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
    except UserLastActiveAdminRequiredError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "USER_LAST_ACTIVE_ADMIN_REQUIRED",
            "O último administrador ativo não pode ser desativado ou rebaixado.",
            [{"field": "role"}, {"field": "active"}],
        )
