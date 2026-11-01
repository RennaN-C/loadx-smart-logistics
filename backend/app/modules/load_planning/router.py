import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.integrations.ai import AIProvider, get_ai_provider
from app.modules.access_profiles.catalog import Permission, has_permission
from app.modules.auth.dependencies import require_permission
from app.modules.load_planning.explanation_service import (
    LoadPlanExplanationForbiddenError,
    LoadPlanExplanationInvalidPlanError,
    LoadPlanExplanationNotFoundError,
    LoadPlanExplanationService,
)
from app.modules.load_planning.models import LoadPlan
from app.modules.load_planning.schemas import (
    LoadPlanContinuityRead,
    LoadPlanCreate,
    LoadPlanExplanationRead,
    LoadPlanListRead,
    LoadPlanRead,
    LoadPlanStatus,
    LoadPlanVisualizationRead,
    OperationScope,
    TruckComparisonCreate,
    TruckComparisonRead,
    map_load_plan_read,
    map_load_plan_visualization,
    map_truck_comparison,
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
LoadPlanReader = Annotated[User, Depends(require_permission("loadx.planning.read"))]
LoadPlanManager = Annotated[User, Depends(require_permission("loadx.planning.create"))]
LoadPlanExplainer = Annotated[User, Depends(require_permission("loadx.planning.read"))]


LoadPlanApprover = Annotated[
    User, Depends(require_permission("loadx.planning.approve"))
]


def get_load_planning_service(
    db: Annotated[Session, Depends(get_db)],
) -> LoadPlanningService:
    return LoadPlanningService(db)


def get_load_plan_explanation_service(
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
) -> LoadPlanExplanationService:
    return LoadPlanExplanationService(
        db,
        provider,
        timeout_seconds=settings.ai_explanation_timeout_seconds,
    )


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
        details = (
            [
                {
                    "field": "truck_ids",
                    "ids": [str(truck_id) for truck_id in error.truck_ids],
                }
            ]
            if error.truck_ids
            else [{"field": "truck_id"}]
        )
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "LOAD_PLAN_TRUCK_NOT_FOUND",
            "Caminhão do plano de carga não encontrado.",
            details,
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
        details = (
            [
                {
                    "field": "truck_ids",
                    "ids": [str(truck_id) for truck_id in error.truck_ids],
                }
            ]
            if error.truck_ids
            else [{"field": "truck_id"}]
        )
        return error_response(
            status.HTTP_409_CONFLICT,
            "LOAD_PLAN_TRUCK_INACTIVE",
            "O caminhão selecionado está inativo.",
            details,
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


@router.get(
    "",
    response_model=PageResponse[LoadPlanListRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_load_plans(
    pagination: Pagination,
    current_user: LoadPlanReader,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
    plan_status: Annotated[LoadPlanStatus | None, Query(alias="status")] = None,
    truck_id: uuid.UUID | None = None,
    operation_scope: OperationScope = "all",
) -> PageResponse[LoadPlanListRead] | JSONResponse:
    include_operations = all(
        has_permission(current_user, permission)
        for permission in (
            Permission.TRIPS_READ,
            Permission.ORDERS_READ,
            Permission.LOADING_READ,
        )
    )
    if operation_scope != "all" and not include_operations:
        return error_response(
            403,
            "AUTH_FORBIDDEN",
            "Usuário sem permissão para esta consulta operacional.",
        )
    result = service.list_load_plans(
        pagination,
        requester_role=current_user.role,
        status=plan_status,
        truck_id=truck_id,
        include_operations=include_operations,
        operation_scope=operation_scope,
    )
    return to_page_response(
        result,
        (
            LoadPlanListRead.model_validate(item, from_attributes=True)
            for item in result.items
        ),
    )


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
        return map_load_plan_read(
            load_plan,
            orders_ready_for_approval=service.orders_ready_for_approval(load_plan),
        )
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


@router.post(
    "/compare-trucks",
    response_model=list[TruckComparisonRead],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def compare_trucks(
    data: TruckComparisonCreate,
    current_user: LoadPlanManager,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
) -> list[TruckComparisonRead] | JSONResponse:
    del current_user
    try:
        comparisons = service.compare_trucks(data)
        return [map_truck_comparison(comparison) for comparison in comparisons]
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
    distribution_id, distribution_status, part_status, is_current_part = (
        service.get_distribution_state_for_plan(load_plan_id)
    )
    return map_load_plan_read(
        load_plan,
        distribution_id=distribution_id,
        distribution_status=distribution_status,
        part_status=part_status,
        is_current_part=is_current_part,
        orders_ready_for_approval=service.orders_ready_for_approval(load_plan),
    )


@router.get(
    "/{load_plan_id}/continuity",
    response_model=LoadPlanContinuityRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_load_plan_continuity(
    load_plan_id: uuid.UUID,
    current_user: LoadPlanReader,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
) -> LoadPlanContinuityRead | JSONResponse:
    try:
        plan = service.get_load_plan(load_plan_id)
    except LoadPlanNotFoundError:
        return _not_found_response()
    forbidden = _ensure_read_access(plan, current_user)
    if forbidden is not None:
        return forbidden
    return service.get_continuity(
        plan,
        requester_role=current_user.role,
        can_read_trips=has_permission(current_user, Permission.TRIPS_READ),
        can_read_operations=all(
            has_permission(current_user, p)
            for p in (
                Permission.TRIPS_READ,
                Permission.ORDERS_READ,
                Permission.LOADING_READ,
            )
        ),
    )


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
    "/{load_plan_id}/explain",
    response_model=LoadPlanExplanationRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def explain_load_plan(
    load_plan_id: uuid.UUID,
    current_user: LoadPlanExplainer,
    service: Annotated[
        LoadPlanExplanationService,
        Depends(get_load_plan_explanation_service),
    ],
) -> LoadPlanExplanationRead | JSONResponse:
    try:
        result = service.explain(
            load_plan_id,
            requester_role=current_user.role,
        )
    except LoadPlanExplanationNotFoundError:
        return _not_found_response()
    except LoadPlanExplanationForbiddenError:
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "AUTH_FORBIDDEN",
            "Usuário sem permissão para esta ação.",
        )
    except LoadPlanExplanationInvalidPlanError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "LOAD_PLAN_EXPLANATION_INVALID_PLAN",
            "O plano persistido não pode ser explicado.",
            [{"field": "id"}],
        )
    return LoadPlanExplanationRead(
        load_plan_id=result.load_plan_id,
        source=result.source,
        explanation=result.explanation,
        algorithm_version=result.algorithm_version,
    )


@router.post(
    "/{load_plan_id}/approve",
    response_model=LoadPlanRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def approve_load_plan(
    load_plan_id: uuid.UUID,
    current_user: LoadPlanApprover,
    service: Annotated[LoadPlanningService, Depends(get_load_planning_service)],
) -> LoadPlanRead | JSONResponse:
    try:
        load_plan = service.approve_load_plan(
            load_plan_id,
            changed_by=current_user.id,
        )
        return map_load_plan_read(
            load_plan,
            orders_ready_for_approval=service.orders_ready_for_approval(load_plan),
        )
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
        return map_load_plan_read(
            load_plan,
            orders_ready_for_approval=service.orders_ready_for_approval(load_plan),
        )
    except LoadPlanNotFoundError:
        return _not_found_response()
    except LoadPlanSourceChangedError:
        return error_response(
            409,
            "LOAD_PLAN_SOURCE_CHANGED",
            "Use o contrato da distribuição para reprocessar esta parte.",
        )
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
