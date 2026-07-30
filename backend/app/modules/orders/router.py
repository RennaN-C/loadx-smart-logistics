import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate, OrderRead, OrderUpdate
from app.modules.orders.service import (
    OrderCustomerNotFoundError,
    OrderNotFoundError,
    OrderProductNotFoundError,
    OrderService,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(db: Annotated[Session, Depends(get_db)]) -> OrderService:
    return OrderService(db)


def error_response(status_code: int, code: str, message: str, details: list[Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or [],
        },
    )


@router.get("", response_model=list[OrderRead])
def list_orders(service: Annotated[OrderService, Depends(get_order_service)]) -> list[Order]:
    return list(service.list_orders())


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
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
            [{"field": "items.product_id", "ids": [str(product_id) for product_id in exc.product_ids]}],
        )


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: uuid.UUID,
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


@router.patch("/{order_id}", response_model=OrderRead)
def update_order(
    order_id: uuid.UUID,
    data: OrderUpdate,
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
            [{"field": "items.product_id", "ids": [str(product_id) for product_id in exc.product_ids]}],
        )
