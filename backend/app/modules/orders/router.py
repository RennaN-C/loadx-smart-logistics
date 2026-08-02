import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate, OrderRead, OrderUpdate
from app.modules.orders.service import (
    OrderCustomerNotFoundError,
    OrderNotFoundError,
    OrderProductNotFoundError,
    OrderService,
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
    response_model=list[OrderRead],
    responses=openapi_error_responses(401, 403),
)
def list_orders(
    _current_user: OrderReader,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> list[Order]:
    return list(service.list_orders())


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def create_order(
    data: OrderCreate,
    _current_user: OrderManager,
    service: Annotated[OrderService, Depends(get_order_service)],
) -> Order | JSONResponse:
    try:
        return service.create_order(data)
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
    responses=openapi_error_responses(401, 403, 404, 422),
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
