import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.integrations.evidence_storage import EvidenceStorage, EvidenceStorageError
from app.modules.attachments.schemas import (
    AttachmentCreate,
    AttachmentRead,
    AttachmentResource,
    AttachmentRevoke,
)
from app.modules.attachments.service import (
    AttachmentForbiddenError,
    AttachmentIdentityConflictError,
    AttachmentNotFoundError,
    AttachmentRevokedError,
    AttachmentService,
)
from app.modules.auth.dependencies import get_current_user
from app.modules.deliveries.evidence_content import EvidenceContentInvalidError
from app.modules.deliveries.evidence_router import get_evidence_storage
from app.modules.deliveries.service import (
    DeliveryNotFoundError,
    TripAccessForbiddenError,
    TripNotFoundError,
)
from app.modules.occurrences.service import OccurrenceNotFoundError
from app.modules.orders.service import OrderNotFoundError
from app.modules.users.models import User
from app.modules.users.service import UserNotFoundError

router = APIRouter(
    prefix="/attachments/{resource_type}/{resource_id}",
    tags=["attachments"],
    responses=openapi_error_responses(401, 403, 404, 409, 422, 503),
)
Actor = Annotated[User, Depends(get_current_user)]


def get_attachment_service(
    db: Annotated[Session, Depends(get_db)],
) -> AttachmentService:
    return AttachmentService(db)


Service = Annotated[AttachmentService, Depends(get_attachment_service)]


def get_attachment_storage() -> EvidenceStorage:
    try:
        return get_evidence_storage()
    except ApiError:
        raise ApiError(
            503,
            "ATTACHMENT_STORAGE_UNAVAILABLE",
            "Armazenamento de anexos indisponível.",
        ) from None


Storage = Annotated[EvidenceStorage, Depends(get_attachment_storage)]

ERRORS = {
    AttachmentForbiddenError: (
        403,
        "AUTH_FORBIDDEN",
        "Usuário sem permissão para este recurso.",
    ),
    TripAccessForbiddenError: (
        403,
        "AUTH_FORBIDDEN",
        "Usuário sem permissão para este recurso.",
    ),
    UserNotFoundError: (
        403,
        "AUTH_FORBIDDEN",
        "Usuário sem permissão para este recurso.",
    ),
    AttachmentNotFoundError: (
        404,
        "ATTACHMENT_NOT_FOUND",
        "Anexo não encontrado neste recurso.",
    ),
    AttachmentIdentityConflictError: (
        409,
        "ATTACHMENT_IDENTITY_CONFLICT",
        "Identidade do evento reutilizada de forma incompatível.",
    ),
    AttachmentRevokedError: (409, "ATTACHMENT_REVOKED", "O anexo foi removido."),
    EvidenceContentInvalidError: (
        422,
        "ATTACHMENT_CONTENT_INVALID",
        "Envie uma imagem PNG/JPEG válida de até 5 MiB.",
    ),
    EvidenceStorageError: (
        503,
        "ATTACHMENT_STORAGE_UNAVAILABLE",
        "Armazenamento de anexos indisponível.",
    ),
    **{
        error: (
            404,
            "ATTACHMENT_RESOURCE_NOT_FOUND",
            "Recurso do anexo não encontrado.",
        )
        for error in (
            OrderNotFoundError,
            TripNotFoundError,
            DeliveryNotFoundError,
            OccurrenceNotFoundError,
        )
    },
}
ATTACHMENT_ERRORS = tuple(ERRORS)


def attachment_error(error: Exception) -> JSONResponse:
    return error_response(*ERRORS[type(error)])


@router.post("", response_model=AttachmentRead)
def register_attachment(
    resource_type: AttachmentResource,
    resource_id: uuid.UUID,
    payload: AttachmentCreate,
    actor: Actor,
    service: Service,
    storage: Storage,
):
    service.storage = storage
    try:
        return service.register(resource_type, resource_id, payload, current_user=actor)
    except ATTACHMENT_ERRORS as error:
        return attachment_error(error)


@router.get("", response_model=PageResponse[AttachmentRead])
def list_attachments(
    resource_type: AttachmentResource,
    resource_id: uuid.UUID,
    actor: Actor,
    service: Service,
    pagination: Pagination,
):
    try:
        page = service.list(resource_type, resource_id, pagination, current_user=actor)
        return to_page_response(page, page.items)
    except ATTACHMENT_ERRORS as error:
        return attachment_error(error)


@router.get("/{attachment_id}", response_model=AttachmentRead)
def get_attachment(
    resource_type: AttachmentResource,
    resource_id: uuid.UUID,
    attachment_id: uuid.UUID,
    actor: Actor,
    service: Service,
):
    try:
        return service.get(
            resource_type, resource_id, attachment_id, current_user=actor
        )
    except ATTACHMENT_ERRORS as error:
        return attachment_error(error)


@router.get(
    "/{attachment_id}/content",
    response_class=Response,
    responses={
        200: {
            "content": {
                mime: {"schema": {"type": "string", "format": "binary"}}
                for mime in ("image/png", "image/jpeg")
            }
        }
    },
)
def download_attachment(
    resource_type: AttachmentResource,
    resource_id: uuid.UUID,
    attachment_id: uuid.UUID,
    actor: Actor,
    service: Service,
    storage: Storage,
):
    service.storage = storage
    try:
        content, media_type = service.download(
            resource_type, resource_id, attachment_id, current_user=actor
        )
        extension = "png" if media_type == "image/png" else "jpg"
        return Response(
            content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{attachment_id}.{extension}"',
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )
    except ATTACHMENT_ERRORS as error:
        return attachment_error(error)


@router.post("/{attachment_id}/revoke", response_model=AttachmentRead)
def revoke_attachment(
    resource_type: AttachmentResource,
    resource_id: uuid.UUID,
    attachment_id: uuid.UUID,
    _payload: AttachmentRevoke,
    actor: Actor,
    service: Service,
):
    try:
        return service.revoke(
            resource_type, resource_id, attachment_id, current_user=actor
        )
    except ATTACHMENT_ERRORS as error:
        return attachment_error(error)
