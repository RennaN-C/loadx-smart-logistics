import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.load_planning.models import LoadPlan
from app.modules.load_planning.schemas import (
    LoadPlanCreate,
    LoadPlanRead,
    LoadPlanVisualizationRead,
    map_load_plan_read,
    map_load_plan_visualization,
)
from app.modules.load_planning.service import (
    InvalidLoadPlanInputError,
    LoadPlanHasRejectionsError,
    LoadPlanInvalidStatusError,
    LoadPlanningService,
    LoadPlanNotFoundError,
    LoadPlanOrdersNotEligibleError,
    LoadPlanOrdersNotFoundError,
    LoadPlanProductsNotFoundError,
    LoadPlanSourceChangedError,
    LoadPlanTruckInactiveError,
    LoadPlanTruckNotFoundError,
    LoadPlanVolumeLimitExceededError,
)
from app.modules.users.models import User

router = APIRouter(prefix="/load-plans", tags=["load-plans"])
LoadPlanReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "CHECKER", "LOGISTICS_MANAGER")),
]
LoadPlanManager = Annotated[
    User,
    Depends(require_roles("LOGISTICS_MANAGER")),
]


def get_load_planning_service(
    db: Annotated[Session, Depends(get_db)],
) -> LoadPlanningService:
    return LoadPlanningService(db)


def _not_found_response() -> JSONResponse:
    return error_response(
        status.HTTP_404_NOT_FOUND,
        "LOAD_PLAN_NOT_FOUND",
        "Plano de carga não encontrado.",
        [{"field": "id"}],
    )


def _ensure_read_access(
    load_plan: LoadPlan,
    current_user: User,
) -> JSONResponse | None:
    if current_user.role == "CHECKER" and load_plan.status != "APPROVED":
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "AUTH_FORBIDDEN",
            "Usuário sem permissão para esta ação.",
        )
    return None


def _calculation_error_response(error: Exception) -> JSONResponse | None:
    if isinstance(error, LoadPlanTruckNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "LOAD_PLAN_TRUCK_NOT_FOUND",
            "Caminhão do plano de carga não encontrado.",
            [{"field": "truck_id"}],
        )
    if isinstance(error, LoadPlanOrdersNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "LOAD_PLAN_ORDER_NOT_FOUND",
            "Um ou mais pedidos do plano de carga não foram encontrados.",
            [
                {
                    "field": "order_ids",
                    "ids": [str(order_id) for order_id in error.order_ids],
                }
            ],
        )
    if isinstance(error, LoadPlanProductsNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "LOAD_PLAN_PRODUCT_NOT_FOUND",
            "Um ou mais produtos do plano de carga não foram encontrados.",
            [
                {
                    "field": "items.product_id",
                    "ids": [str(product_id) for product_id in error.product_ids],
                }
            ],
        )
    if isinstance(error, LoadPlanTruckInactiveError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "LOAD_PLAN_TRUCK_INACTIVE",
            "O caminhão selecionado está inativo.",
            [{"field": "truck_id"}],
        )
    if isinstance(error, LoadPlanOrdersNotEligibleError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "LOAD_PLAN_ORDER_NOT_ELIGIBLE",
            "Um ou mais pedidos não estão elegíveis para este planejamento.",
            [
                {
                    "field": "order_ids",
                    "orders": [
                        {"id": str(order_id), "status": order_status}
                        for order_id, order_status in error.order_statuses
                    ],
                }
            ],
        )
    if isinstance(error, LoadPlanVolumeLimitExceededError):
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error.code,
            "O plano excede o limite síncrono de volumes.",
            [
                {
                    "field": "order_ids",
                    "volume_count": error.volume_count,
                    "max_volumes": error.max_volumes,
                }
            ],
        )
    if isinstance(error, InvalidLoadPlanInputError):
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_LOAD_PLAN_INPUT",
            "Os dados do plano de carga são inválidos.",
            [{"field": error.field_name, "message": error.reason}],
        )
    return None


@router.post(
    "",
    response_model=LoadPlanRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def create_load_plan(
    data: LoadPlanCreate,
    current_user: LoadPlanManager,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
) -> LoadPlanRead | JSONResponse:
    try:
        load_plan = service.create_load_plan(data, changed_by=current_user.id)
        return map_load_plan_read(load_plan)
    except (
        InvalidLoadPlanInputError,
        LoadPlanOrdersNotEligibleError,
        LoadPlanOrdersNotFoundError,
        LoadPlanProductsNotFoundError,
        LoadPlanTruckInactiveError,
        LoadPlanTruckNotFoundError,
        LoadPlanVolumeLimitExceededError,
    ) as exc:
        response = _calculation_error_response(exc)
        if response is None:
            raise
        return response


@router.get(
    "/{load_plan_id}",
    response_model=LoadPlanRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_load_plan(
    load_plan_id: uuid.UUID,
    current_user: LoadPlanReader,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
) -> LoadPlanRead | JSONResponse:
    try:
        load_plan = service.get_load_plan(load_plan_id)
    except LoadPlanNotFoundError:
        return _not_found_response()
    forbidden = _ensure_read_access(load_plan, current_user)
    if forbidden is not None:
        return forbidden
    return map_load_plan_read(load_plan)


@router.get(
    "/{load_plan_id}/visualization",
    response_model=LoadPlanVisualizationRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_load_plan_visualization(
    load_plan_id: uuid.UUID,
    current_user: LoadPlanReader,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
) -> LoadPlanVisualizationRead | JSONResponse:
    try:
        load_plan = service.get_load_plan(load_plan_id)
    except LoadPlanNotFoundError:
        return _not_found_response()
    forbidden = _ensure_read_access(load_plan, current_user)
    if forbidden is not None:
        return forbidden
    return map_load_plan_visualization(load_plan)


@router.post(
    "/{load_plan_id}/approve",
    response_model=LoadPlanRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def approve_load_plan(
    load_plan_id: uuid.UUID,
    current_user: LoadPlanManager,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
) -> LoadPlanRead | JSONResponse:
    try:
        load_plan = service.approve_load_plan(
            load_plan_id,
            changed_by=current_user.id,
        )
        return map_load_plan_read(load_plan)
    except LoadPlanNotFoundError:
        return _not_found_response()
    except LoadPlanInvalidStatusError as exc:
        return error_response(
            status.HTTP_409_CONFLICT,
            "LOAD_PLAN_INVALID_STATUS",
            "O estado atual do plano não permite aprovação.",
            [{"field": "status", "value": exc.current_status}],
        )
    except LoadPlanHasRejectionsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "LOAD_PLAN_HAS_REJECTIONS",
            "Plano com volumes rejeitados não pode ser aprovado.",
            [{"field": "unloaded_count"}],
        )
    except LoadPlanOrdersNotEligibleError as exc:
        response = _calculation_error_response(exc)
        if response is None:
            raise
        return response
    except LoadPlanSourceChangedError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "LOAD_PLAN_SOURCE_CHANGED",
            "As entidades de origem do plano não estão mais disponíveis.",
        )


@router.post(
    "/{load_plan_id}/recalculate",
    response_model=LoadPlanRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def recalculate_load_plan(
    load_plan_id: uuid.UUID,
    current_user: LoadPlanManager,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
) -> LoadPlanRead | JSONResponse:
    try:
        load_plan = service.recalculate_load_plan(
            load_plan_id,
            changed_by=current_user.id,
        )
        return map_load_plan_read(load_plan)
    except LoadPlanNotFoundError:
        return _not_found_response()
    except (
        InvalidLoadPlanInputError,
        LoadPlanOrdersNotEligibleError,
        LoadPlanOrdersNotFoundError,
        LoadPlanProductsNotFoundError,
        LoadPlanTruckInactiveError,
        LoadPlanTruckNotFoundError,
        LoadPlanVolumeLimitExceededError,
    ) as exc:
        response = _calculation_error_response(exc)
        if response is None:
            raise
        return response
