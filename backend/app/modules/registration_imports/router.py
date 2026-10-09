import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.registration_imports.schemas import (
    ImportConfirm,
    ImportEntity,
    ImportFile,
    ImportListRead,
    ImportPreview,
    ImportRead,
)
from app.modules.registration_imports.service import (
    ImportForbiddenError,
    ImportIdentityConflictError,
    ImportNotFoundError,
    ImportPreviewMismatchError,
    ImportService,
)
from app.modules.users.models import User
from app.modules.users.service import UserNotFoundError

router = APIRouter(
    prefix="/registration-imports",
    tags=["registration-imports"],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
Actor = Annotated[User, Depends(require_roles("ADMIN", "LOGISTICS_MANAGER"))]


def get_import_service(db: Annotated[Session, Depends(get_db)]) -> ImportService:
    return ImportService(db)


Service = Annotated[ImportService, Depends(get_import_service)]
ERRORS = {
    ImportForbiddenError: (
        403,
        "AUTH_FORBIDDEN",
        "Usuário sem permissão para importar cadastros.",
    ),
    UserNotFoundError: (
        403,
        "AUTH_FORBIDDEN",
        "Usuário sem permissão para importar cadastros.",
    ),
    ImportNotFoundError: (
        404,
        "IMPORT_NOT_FOUND",
        "Resultado de importação não encontrado.",
    ),
    ImportIdentityConflictError: (
        409,
        "IMPORT_IDENTITY_CONFLICT",
        "Identidade do evento reutilizada de forma incompatível.",
    ),
    ImportPreviewMismatchError: (
        409,
        "IMPORT_PREVIEW_MISMATCH",
        "Arquivo diferente da prévia. Valide novamente antes de confirmar.",
    ),
}
IMPORT_ERRORS = tuple(ERRORS)


def import_error(error: Exception) -> JSONResponse:
    return error_response(*ERRORS[type(error)])


@router.get("", response_model=PageResponse[ImportListRead])
def list_imports(
    pagination: Pagination,
    actor: Actor,
    service: Service,
    entity_type: ImportEntity | None = None,
):
    try:
        page = service.list(pagination, entity_type, current_user=actor)
        return to_page_response(page, page.items)
    except IMPORT_ERRORS as error:
        return import_error(error)


@router.get(
    "/{entity_type}/template",
    response_class=Response,
    responses={
        200: {
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}
        }
    },
)
def download_template(entity_type: ImportEntity, actor: Actor, service: Service):
    try:
        return Response(
            service.template(entity_type, current_user=actor),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{entity_type}-template.csv"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except IMPORT_ERRORS as error:
        return import_error(error)


@router.post("/{entity_type}/preview", response_model=ImportPreview)
def preview_import(
    entity_type: ImportEntity, data: ImportFile, actor: Actor, service: Service
):
    try:
        return service.preview(entity_type, data, current_user=actor)
    except IMPORT_ERRORS as error:
        return import_error(error)


@router.post("/{entity_type}/confirm", response_model=ImportRead)
def confirm_import(
    entity_type: ImportEntity, data: ImportConfirm, actor: Actor, service: Service
):
    try:
        return service.confirm(entity_type, data, current_user=actor)
    except IMPORT_ERRORS as error:
        return import_error(error)


@router.get("/{import_id}", response_model=ImportRead)
def get_import(import_id: uuid.UUID, actor: Actor, service: Service):
    try:
        return service.get(import_id, current_user=actor)
    except IMPORT_ERRORS as error:
        return import_error(error)
