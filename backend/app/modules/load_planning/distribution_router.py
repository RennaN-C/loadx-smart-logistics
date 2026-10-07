import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.load_planning.distribution_schemas import (
    DistributionAction,
    DistributionCreate,
    DistributionNeedRead,
    DistributionNeedRequest,
    DistributionPartReprocess,
    DistributionRead,
)
from app.modules.load_planning.distribution_service import (
    DistributionError,
    LoadDistributionService,
)
from app.modules.load_planning.router import (
    LoadPlanManager,
    LoadPlanReader,
    _calculation_error_response,
)
from app.modules.load_planning.service import (
    InvalidLoadPlanInputError,
    LoadPlanOrdersNotEligibleError,
    LoadPlanOrdersNotFoundError,
    LoadPlanProductsNotFoundError,
    LoadPlanTruckInactiveError,
    LoadPlanTruckNotFoundError,
    LoadPlanVolumeLimitExceededError,
)
from app.modules.trucks.service import TruckOperationConflictError

router = APIRouter(
    prefix="/load-distributions",
    tags=["load-distributions"],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
ERRORS = (
    DistributionError,
    TruckOperationConflictError,
    InvalidLoadPlanInputError,
    LoadPlanOrdersNotEligibleError,
    LoadPlanOrdersNotFoundError,
    LoadPlanProductsNotFoundError,
    LoadPlanTruckInactiveError,
    LoadPlanTruckNotFoundError,
    LoadPlanVolumeLimitExceededError,
)


def get_distribution_service(
    db: Annotated[Session, Depends(get_db)],
) -> LoadDistributionService:
    return LoadDistributionService(db)


Service = Annotated[LoadDistributionService, Depends(get_distribution_service)]


def _error(error: Exception) -> JSONResponse:
    if isinstance(error, DistributionError):
        return error_response(
            error.status,
            error.code,
            "A distribuição não permite esta operação.",
            error.details,
        )
    if isinstance(error, TruckOperationConflictError):
        return error_response(
            409,
            "TRUCK_OPERATION_CONFLICT",
            "Caminhão em outra operação ativa.",
            [{"truck_id": str(error.truck_id)}],
        )
    response = _calculation_error_response(error)
    if response is None:
        raise error
    return response


@router.post("/preflight", response_model=DistributionNeedRead)
def preflight(
    data: DistributionNeedRequest, user: LoadPlanManager, service: Service
) -> DistributionNeedRead | JSONResponse:
    try:
        return service.preflight(data)
    except ERRORS as error:
        return _error(error)


@router.post("", response_model=DistributionRead, status_code=201)
def create(
    data: DistributionCreate, user: LoadPlanManager, service: Service
) -> DistributionRead | JSONResponse:
    try:
        return service.create(data, changed_by=user.id)
    except ERRORS as error:
        return _error(error)


@router.get("/{distribution_id}", response_model=DistributionRead)
def get(
    distribution_id: uuid.UUID, user: LoadPlanReader, service: Service
) -> DistributionRead | JSONResponse:
    try:
        result = service.get(distribution_id)
        if user.role == "CHECKER" and result.status != "APPROVED":
            return error_response(
                403, "AUTH_FORBIDDEN", "Usuário sem permissão para esta ação."
            )
        return result
    except ERRORS as error:
        return _error(error)


@router.post("/{distribution_id}/approve", response_model=DistributionRead)
def approve(
    distribution_id: uuid.UUID,
    payload: DistributionAction,
    user: LoadPlanManager,
    service: Service,
) -> DistributionRead | JSONResponse:
    try:
        return service.approve(distribution_id, changed_by=user.id)
    except ERRORS as error:
        return _error(error)


@router.post("/{distribution_id}/cancel", response_model=DistributionRead)
def cancel(
    distribution_id: uuid.UUID,
    payload: DistributionAction,
    user: LoadPlanManager,
    service: Service,
) -> DistributionRead | JSONResponse:
    try:
        return service.cancel(distribution_id, changed_by=user.id)
    except ERRORS as error:
        return _error(error)


@router.post(
    "/{distribution_id}/parts/{part_id}/approve", response_model=DistributionRead
)
def approve_part(
    distribution_id: uuid.UUID,
    part_id: uuid.UUID,
    payload: DistributionAction,
    user: LoadPlanManager,
    service: Service,
) -> DistributionRead | JSONResponse:
    try:
        return service.approve(distribution_id, part_id=part_id, changed_by=user.id)
    except ERRORS as error:
        return _error(error)


@router.post(
    "/{distribution_id}/parts/{part_id}/cancel", response_model=DistributionRead
)
def cancel_part(
    distribution_id: uuid.UUID,
    part_id: uuid.UUID,
    payload: DistributionAction,
    user: LoadPlanManager,
    service: Service,
) -> DistributionRead | JSONResponse:
    try:
        return service.cancel(distribution_id, part_id=part_id, changed_by=user.id)
    except ERRORS as error:
        return _error(error)


@router.post(
    "/{distribution_id}/parts/{part_id}/reprocess", response_model=DistributionRead
)
def reprocess(
    distribution_id: uuid.UUID,
    part_id: uuid.UUID,
    data: DistributionPartReprocess,
    user: LoadPlanManager,
    service: Service,
) -> DistributionRead | JSONResponse:
    try:
        return service.reprocess(distribution_id, part_id, data, changed_by=user.id)
    except ERRORS as error:
        return _error(error)
