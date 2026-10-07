import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.integrations.evidence_storage import (
    EvidenceStorage,
    EvidenceStorageError,
    LocalEvidenceStorage,
)
from app.modules.deliveries.evidence_content import EvidenceContentInvalidError
from app.modules.deliveries.evidence_schemas import (
    DeliveryEvidenceCreate,
    DeliveryEvidenceRead,
    DeliveryEvidenceRevoke,
)
from app.modules.deliveries.evidence_service import (
    DeliveryEvidenceService,
    EvidenceIdentityConflictError,
    EvidenceNotFoundError,
    EvidenceRevokedError,
)
from app.modules.deliveries.router import (
    TRIP_SERVICE_ERRORS,
    TripOperator,
    TripReader,
    _trip_error_response,
)

router = APIRouter(
    prefix="/deliveries/{delivery_id}/evidences",
    tags=["delivery-evidences"],
    responses=openapi_error_responses(401, 403, 404, 409, 422, 503),
)


def get_evidence_storage() -> EvidenceStorage:
    if settings.app_env != "local" or settings.evidence_storage_dir is None:
        raise ApiError(
            503,
            "EVIDENCE_STORAGE_UNAVAILABLE",
            "Armazenamento de evidências indisponível.",
        )
    try:
        return LocalEvidenceStorage(settings.evidence_storage_dir)
    except EvidenceStorageError:
        raise ApiError(
            503,
            "EVIDENCE_STORAGE_UNAVAILABLE",
            "Armazenamento de evidências indisponível.",
        ) from None


def get_evidence_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[EvidenceStorage, Depends(get_evidence_storage)],
) -> DeliveryEvidenceService:
    return DeliveryEvidenceService(db, storage)


EVIDENCE_ERRORS = (
    *TRIP_SERVICE_ERRORS,
    EvidenceContentInvalidError,
    EvidenceIdentityConflictError,
    EvidenceNotFoundError,
    EvidenceRevokedError,
    EvidenceStorageError,
)

EvidenceService = Annotated[DeliveryEvidenceService, Depends(get_evidence_service)]


def _evidence_error(error: Exception) -> JSONResponse:
    if isinstance(error, TRIP_SERVICE_ERRORS):
        return _trip_error_response(error)
    errors = {
        EvidenceContentInvalidError: (
            422,
            "EVIDENCE_CONTENT_INVALID",
            "A evidência exige imagem PNG/JPEG válida nos limites permitidos.",
        ),
        EvidenceIdentityConflictError: (
            409,
            "EVIDENCE_IDENTITY_CONFLICT",
            "Identidade do evento reutilizada de forma incompatível.",
        ),
        EvidenceNotFoundError: (
            404,
            "EVIDENCE_NOT_FOUND",
            "Evidência não encontrada nesta entrega.",
        ),
        EvidenceRevokedError: (409, "EVIDENCE_REVOKED", "A evidência foi revogada."),
        EvidenceStorageError: (
            503,
            "EVIDENCE_STORAGE_UNAVAILABLE",
            "Armazenamento de evidências indisponível.",
        ),
    }
    values = errors.get(type(error))
    if values is None:
        raise error
    return error_response(*values)


@router.post("", response_model=DeliveryEvidenceRead)
def register_evidence(
    delivery_id: uuid.UUID,
    payload: DeliveryEvidenceCreate,
    current_user: TripOperator,
    service: EvidenceService,
):
    try:
        return service.register(delivery_id, payload, current_user=current_user)
    except EVIDENCE_ERRORS as error:
        return _evidence_error(error)


@router.get("", response_model=PageResponse[DeliveryEvidenceRead])
def list_evidences(
    delivery_id: uuid.UUID,
    current_user: TripReader,
    service: EvidenceService,
    pagination: Pagination,
):
    try:
        result = service.list(delivery_id, pagination, current_user=current_user)
        return to_page_response(result, result.items)
    except EVIDENCE_ERRORS as error:
        return _evidence_error(error)


@router.get("/{evidence_id}", response_model=DeliveryEvidenceRead)
def get_evidence(
    delivery_id: uuid.UUID,
    evidence_id: uuid.UUID,
    current_user: TripReader,
    service: EvidenceService,
):
    try:
        return service.get(delivery_id, evidence_id, current_user=current_user)
    except EVIDENCE_ERRORS as error:
        return _evidence_error(error)


@router.get(
    "/{evidence_id}/content",
    response_class=Response,
    responses={
        200: {
            "content": {
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
            }
        }
    },
)
def download_evidence(
    delivery_id: uuid.UUID,
    evidence_id: uuid.UUID,
    current_user: TripReader,
    service: EvidenceService,
):
    try:
        content, media_type = service.download(
            delivery_id, evidence_id, current_user=current_user
        )
        extension = "png" if media_type == "image/png" else "jpg"
        return Response(
            content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{evidence_id}.{extension}"',
                "X-Content-Type-Options": "nosniff",
            },
        )
    except EVIDENCE_ERRORS as error:
        return _evidence_error(error)


@router.post("/{evidence_id}/revoke", response_model=DeliveryEvidenceRead)
def revoke_evidence(
    delivery_id: uuid.UUID,
    evidence_id: uuid.UUID,
    _payload: DeliveryEvidenceRevoke,
    current_user: TripOperator,
    service: EvidenceService,
):
    try:
        return service.revoke(delivery_id, evidence_id, current_user=current_user)
    except EVIDENCE_ERRORS as error:
        return _evidence_error(error)
