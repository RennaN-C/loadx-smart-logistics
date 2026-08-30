import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.occurrences.models import Occurrence
from app.modules.occurrences.schemas import OccurrenceCreate, OccurrenceRead
from app.modules.occurrences.service import (
    OccurrenceAccessForbiddenError,
    OccurrenceDeliveryNotFoundError,
    OccurrenceDeliveryTripMismatchError,
    OccurrenceService,
    OccurrenceTripNotFoundError,
)
from app.modules.users.models import User

router = APIRouter(tags=["occurrences"])
OccurrenceOperator = Annotated[
    User,
    Depends(require_roles("LOGISTICS_MANAGER", "DRIVER")),
]
OccurrenceReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "LOGISTICS_MANAGER", "DRIVER")),
]
OCCURRENCE_SERVICE_ERRORS = (
    OccurrenceAccessForbiddenError,
    OccurrenceDeliveryNotFoundError,
    OccurrenceDeliveryTripMismatchError,
    OccurrenceTripNotFoundError,
)


def get_occurrence_service(
    db: Annotated[Session, Depends(get_db)],
) -> OccurrenceService:
    return OccurrenceService(db)


@router.post(
    "/occurrences",
    response_model=OccurrenceRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def create_occurrence(
    data: OccurrenceCreate,
    current_user: OccurrenceOperator,
    service: Annotated[OccurrenceService, Depends(get_occurrence_service)],
) -> Occurrence | JSONResponse:
    try:
        return service.register_occurrence(data, current_user=current_user)
    except OCCURRENCE_SERVICE_ERRORS as exc:
        return _occurrence_error_response(exc)


@router.get(
    "/trips/{trip_id}/occurrences",
    response_model=list[OccurrenceRead],
    responses=openapi_error_responses(401, 403, 404, 422),
)
def list_trip_occurrences(
    trip_id: uuid.UUID,
    current_user: OccurrenceReader,
    service: Annotated[OccurrenceService, Depends(get_occurrence_service)],
) -> list[Occurrence] | JSONResponse:
    try:
        return service.list_trip_occurrences(trip_id, current_user=current_user)
    except OCCURRENCE_SERVICE_ERRORS as exc:
        return _occurrence_error_response(exc)


def _occurrence_error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, OccurrenceAccessForbiddenError):
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "AUTH_FORBIDDEN",
            "Usuário sem permissão para esta ação.",
        )
    if isinstance(exc, OccurrenceTripNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "TRIP_NOT_FOUND",
            "Viagem não encontrada.",
            [{"field": "trip_id"}],
        )
    if isinstance(exc, OccurrenceDeliveryNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "DELIVERY_NOT_FOUND",
            "Entrega não encontrada.",
            [{"field": "delivery_id"}],
        )
    if isinstance(exc, OccurrenceDeliveryTripMismatchError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "OCCURRENCE_DELIVERY_TRIP_MISMATCH",
            "A entrega não pertence à viagem informada.",
        )
    raise exc
