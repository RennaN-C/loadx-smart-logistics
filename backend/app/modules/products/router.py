import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.modules.products.service import (
    ProductCodeAlreadyExistsError,
    ProductNotFoundError,
    ProductService,
)

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(db: Annotated[Session, Depends(get_db)]) -> ProductService:
    return ProductService(db)


def error_response(status_code: int, code: str, message: str, details: list[Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or [],
        },
    )


@router.get("", response_model=list[ProductRead])
def list_products(service: Annotated[ProductService, Depends(get_product_service)]) -> list[Product]:
    return list(service.list_products())


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Product | JSONResponse:
    try:
        return service.create_product(data)
    except ProductCodeAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "PRODUCT_CODE_ALREADY_EXISTS",
            "Já existe um produto cadastrado com este código.",
            [{"field": "code"}],
        )


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: uuid.UUID,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Product | JSONResponse:
    try:
        return service.get_product(product_id)
    except ProductNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "PRODUCT_NOT_FOUND",
            "Produto não encontrado.",
            [{"field": "id"}],
        )


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Product | JSONResponse:
    try:
        return service.update_product(product_id, data)
    except ProductNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "PRODUCT_NOT_FOUND",
            "Produto não encontrado.",
            [{"field": "id"}],
        )
    except ProductCodeAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "PRODUCT_CODE_ALREADY_EXISTS",
            "Já existe um produto cadastrado com este código.",
            [{"field": "code"}],
        )
