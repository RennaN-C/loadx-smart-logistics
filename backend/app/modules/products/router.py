import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductRead, ProductUpdate
from app.modules.products.service import (
    ProductCodeAlreadyExistsError,
    ProductNotFoundError,
    ProductService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/products", tags=["products"])
ProductReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "CHECKER", "LOGISTICS_MANAGER")),
]
ProductManager = Annotated[
    User,
    Depends(require_roles("LOGISTICS_MANAGER")),
]


def get_product_service(db: Annotated[Session, Depends(get_db)]) -> ProductService:
    return ProductService(db)


@router.get(
    "",
    response_model=PageResponse[ProductRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_products(
    pagination: Pagination,
    _current_user: ProductReader,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> PageResponse[ProductRead]:
    result = service.list_products(pagination)
    return to_page_response(
        result,
        (ProductRead.model_validate(product) for product in result.items),
    )


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 409, 422),
)
def create_product(
    data: ProductCreate,
    _current_user: ProductManager,
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


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_product(
    product_id: uuid.UUID,
    _current_user: ProductReader,
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


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    _current_user: ProductManager,
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
