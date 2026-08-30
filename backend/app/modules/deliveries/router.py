import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.integrations.whatsapp import WhatsAppProvider, get_whatsapp_provider
from app.modules.auth.dependencies import require_roles
from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.schemas import (
    DeliveryRead,
    DeliveryStatusChange,
    TripCreate,
    TripRead,
    TripStatusChange,
)
from app.modules.deliveries.service import (
    DeliveryNotFoundError,
    DeliveryStatusTransitionNotAllowedError,
    DeliveryTripNotInRouteError,
    TripAccessForbiddenError,
    TripDeliveriesNotFinishedError,
    TripDeliverySequenceConflictError,
    TripDriverInactiveError,
    TripDriverNotFoundError,
    TripLoadingNotFinishedError,
    TripLoadPlanAlreadyAssignedError,
    TripLoadPlanNotApprovedError,
    TripLoadPlanNotFoundError,
    TripNotFoundError,
    TripOrderAlreadyAssignedError,
    TripOrderNotEligibleError,
    TripService,
    TripStatusTransitionNotAllowedError,
)
from app.modules.notifications.service import OperationalNotificationService
from app.modules.users.models import User

router = APIRouter(tags=["trips"])
ManagerUser = Annotated[User, Depends(require_roles("LOGISTICS_MANAGER"))]
TripReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "LOGISTICS_MANAGER", "DRIVER")),
]
TripOperator = Annotated[
    User,
    Depends(require_roles("LOGISTICS_MANAGER", "DRIVER")),
]
TRIP_SERVICE_ERRORS = (
    DeliveryNotFoundError,
    DeliveryStatusTransitionNotAllowedError,
    DeliveryTripNotInRouteError,
    TripAccessForbiddenError,
    TripDeliveriesNotFinishedError,
    TripDeliverySequenceConflictError,
    TripDriverInactiveError,
    TripDriverNotFoundError,
    TripLoadingNotFinishedError,
    TripLoadPlanAlreadyAssignedError,
    TripLoadPlanNotApprovedError,
    TripLoadPlanNotFoundError,
    TripNotFoundError,
    TripOrderAlreadyAssignedError,
    TripOrderNotEligibleError,
    TripStatusTransitionNotAllowedError,
)


def get_trip_service(
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[WhatsAppProvider, Depends(get_whatsapp_provider)],
) -> TripService:
    return TripService(
        db,
        notification_service=OperationalNotificationService(provider),
    )


@router.post(
    "/trips",
    response_model=TripRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def create_trip(
    data: TripCreate,
    current_user: ManagerUser,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> Trip | JSONResponse:
    try:
        return service.create_trip(data, changed_by=current_user.id)
    except TRIP_SERVICE_ERRORS as exc:
        return _trip_error_response(exc)


@router.get(
    "/trips/{trip_id}",
    response_model=TripRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_trip(
    trip_id: uuid.UUID,
    current_user: TripReader,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> Trip | JSONResponse:
    try:
        return service.get_trip(trip_id, current_user=current_user)
    except TRIP_SERVICE_ERRORS as exc:
        return _trip_error_response(exc)


@router.patch(
    "/trips/{trip_id}/status",
    response_model=TripRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def change_trip_status(
    trip_id: uuid.UUID,
    data: TripStatusChange,
    current_user: TripOperator,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> Trip | JSONResponse:
    try:
        return service.change_trip_status(
            trip_id,
            data.status,
            current_user=current_user,
        )
    except TRIP_SERVICE_ERRORS as exc:
        return _trip_error_response(exc)


@router.patch(
    "/deliveries/{delivery_id}/status",
    response_model=DeliveryRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def change_delivery_status(
    delivery_id: uuid.UUID,
    data: DeliveryStatusChange,
    current_user: TripOperator,
    service: Annotated[TripService, Depends(get_trip_service)],
) -> Delivery | JSONResponse:
    try:
        return service.change_delivery_status(
            delivery_id,
            data.status,
            current_user=current_user,
        )
    except TRIP_SERVICE_ERRORS as exc:
        return _trip_error_response(exc)


def _trip_error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, TripAccessForbiddenError):
        return error_response(
            status.HTTP_403_FORBIDDEN,
            "AUTH_FORBIDDEN",
            "Usuário sem permissão para esta ação.",
        )
    if isinstance(exc, TripNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "TRIP_NOT_FOUND",
            "Viagem não encontrada.",
            [{"field": "id"}],
        )
    if isinstance(exc, DeliveryNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "DELIVERY_NOT_FOUND",
            "Entrega não encontrada.",
            [{"field": "id"}],
        )
    if isinstance(exc, TripLoadPlanNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "TRIP_LOAD_PLAN_NOT_FOUND",
            "Plano de carga da viagem não encontrado.",
            [{"field": "load_plan_id"}],
        )
    if isinstance(exc, TripDriverNotFoundError):
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "TRIP_DRIVER_NOT_FOUND",
            "Motorista da viagem não encontrado.",
            [{"field": "driver_id"}],
        )
    if isinstance(exc, TripLoadPlanNotApprovedError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_LOAD_PLAN_NOT_APPROVED",
            "A viagem exige um plano de carga aprovado.",
            [{"field": "load_plan_id"}],
        )
    if isinstance(exc, TripLoadPlanAlreadyAssignedError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_LOAD_PLAN_ALREADY_ASSIGNED",
            "O plano de carga já está vinculado a uma viagem.",
            [{"field": "load_plan_id"}],
        )
    if isinstance(exc, TripDriverInactiveError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_DRIVER_INACTIVE",
            "Motorista inativo não pode receber nova viagem.",
            [{"field": "driver_id"}],
        )
    if isinstance(exc, TripOrderAlreadyAssignedError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_ORDER_ALREADY_ASSIGNED",
            "Um ou mais pedidos já pertencem a outra viagem.",
            [
                {"field": "order_ids", "value": str(order_id)}
                for order_id in exc.order_ids
            ],
        )
    if isinstance(exc, TripDeliverySequenceConflictError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_DELIVERY_SEQUENCE_CONFLICT",
            "Os itens do pedido devem usar a mesma sequência de entrega.",
            [{"field": "order_id", "value": str(exc.order_id)}],
        )
    if isinstance(exc, TripOrderNotEligibleError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_ORDER_NOT_ELIGIBLE",
            "Os pedidos da viagem não estão no estado operacional esperado.",
        )
    if isinstance(exc, TripLoadingNotFinishedError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_LOADING_NOT_FINISHED",
            "A viagem só pode iniciar após a finalização do carregamento.",
        )
    if isinstance(exc, TripDeliveriesNotFinishedError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_DELIVERIES_NOT_FINISHED",
            "A viagem só pode terminar após a conclusão de todas as entregas.",
        )
    if isinstance(exc, DeliveryTripNotInRouteError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "DELIVERY_TRIP_NOT_IN_ROUTE",
            "A entrega só pode avançar durante uma viagem em rota.",
        )
    if isinstance(exc, TripStatusTransitionNotAllowedError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRIP_STATUS_TRANSITION_NOT_ALLOWED",
            "A transição de status da viagem não é permitida.",
            [
                {"field": "old_status", "value": exc.current_status},
                {"field": "new_status", "value": exc.requested_status},
            ],
        )
    if isinstance(exc, DeliveryStatusTransitionNotAllowedError):
        return error_response(
            status.HTTP_409_CONFLICT,
            "DELIVERY_STATUS_TRANSITION_NOT_ALLOWED",
            "A transição de status da entrega não é permitida.",
            [
                {"field": "old_status", "value": exc.current_status},
                {"field": "new_status", "value": exc.requested_status},
            ],
        )
    raise exc
