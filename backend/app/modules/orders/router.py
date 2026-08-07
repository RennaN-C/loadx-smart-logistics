import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.orders.models import Order
from app.modules.orders.schemas import (
    OrderCreate,
    OrderListRead,
    OrderRead,
    OrderStatusChange,
    OrderUpdate,
)
from app.modules.orders.service import (
    OrderCustomerNotFoundError,
    OrderEditNotAllowedError,
    OrderItemsReferencedByLoadPlanError,
    OrderNotFoundError,
    OrderProductNotFoundError,
    OrderService,
    OrderStatusTransitionNotAllowedError,
)
from app.modules.users.models import User

router = APIRouter(prefix="/orders", tags=["orders"])
OrderReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "CHECKER", "LOGISTICS_MANAGER")),
]
OrderManager = Annotated[
    User,
    Depends(require_roles("LOGISTICS_MANAGER")),
]


def get_order_service(db: Annotated[Session, Depends(get_db)]) -> OrderService:
    return OrderService(db)


@router.get(
    "",
    response_model=PageResponse[OrderListRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_orders(
    pagination: Pagination,
    _current_user: OrderReader,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> PageResponse[OrderListRead]:
    result = service.list_orders(pagination)
    return to_page_response(
        result,
        (
            OrderListRead(
                id=order.id,
                customer_id=order.customer_id,
                status=order.status,
                priority=order.priority,
                expected_delivery_at=order.expected_delivery_at,
                created_at=order.created_at,
                item_count=len(order.items),
            )
            for order in result.items
        ),
    )


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def create_order(
    data: OrderCreate,
    current_user: OrderManager,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order | JSONResponse:
    try:
        return service.create_order(data, changed_by=current_user.id)
    except OrderCustomerNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ORDER_CUSTOMER_NOT_FOUND",
            "Cliente do pedido não encontrado.",
            [{"field": "customer_id"}],
        )
    except OrderProductNotFoundError as exc:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ORDER_PRODUCT_NOT_FOUND",
            "Produto do pedido não encontrado.",
            [
                {
                    "field": "items.product_id",
                    "ids": [str(product_id) for product_id in exc.product_ids],
                }
            ],
        )


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_order(
    order_id: uuid.UUID,
    _current_user: OrderReader,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order | JSONResponse:
    try:
        return service.get_order(order_id)
    except OrderNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ORDER_NOT_FOUND",
            "Pedido não encontrado.",
            [{"field": "id"}],
        )


@router.patch(
    "/{order_id}",
    response_model=OrderRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def update_order(
    order_id: uuid.UUID,
    data: OrderUpdate,
    _current_user: OrderManager,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order | JSONResponse:
    try:
        return service.update_order(order_id, data)
    except OrderNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ORDER_NOT_FOUND",
            "Pedido não encontrado.",
            [{"field": "id"}],
        )
    except OrderCustomerNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ORDER_CUSTOMER_NOT_FOUND",
            "Cliente do pedido não encontrado.",
            [{"field": "customer_id"}],
        )
    except OrderProductNotFoundError as exc:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ORDER_PRODUCT_NOT_FOUND",
            "Produto do pedido não encontrado.",
            [
                {
                    "field": "items.product_id",
                    "ids": [str(product_id) for product_id in exc.product_ids],
                }
            ],
        )
    except OrderItemsReferencedByLoadPlanError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "ORDER_ITEMS_REFERENCED_BY_LOAD_PLAN",
            "Os itens deste pedido já pertencem a um plano de carga "
            "e não podem ser substituídos.",
            [{"field": "items"}],
        )
    except OrderEditNotAllowedError as exc:
        return error_response(
            status.HTTP_409_CONFLICT,
            "ORDER_EDIT_NOT_ALLOWED",
            "O pedido precisa estar em DRAFT para ser editado.",
            [{"field": "status", "current_status": exc.current_status}],
        )


@router.patch(
    "/{order_id}/status",
    response_model=OrderRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def change_order_status(
    order_id: uuid.UUID,
    data: OrderStatusChange,
    current_user: OrderManager,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order | JSONResponse:
    try:
        return service.change_order_status(
            order_id,
            data.status,
            changed_by=current_user.id,
        )
    except OrderNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "ORDER_NOT_FOUND",
            "Pedido não encontrado.",
            [{"field": "id"}],
        )
    except OrderStatusTransitionNotAllowedError as exc:
        return error_response(
            status.HTTP_409_CONFLICT,
            "ORDER_STATUS_TRANSITION_NOT_ALLOWED",
            "A transição de status do pedido não é permitida.",
            [
                {
                    "field": "status",
                    "current_status": exc.current_status,
                    "requested_status": exc.requested_status,
                }
            ],
        )
