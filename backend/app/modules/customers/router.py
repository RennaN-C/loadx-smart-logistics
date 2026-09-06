import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.customers.models import Customer
from app.modules.customers.schemas import (
    CustomerCreate,
    CustomerListRead,
    CustomerRead,
    CustomerUpdate,
)
from app.modules.customers.service import (
    CustomerDocumentAlreadyExistsError,
    CustomerNotFoundError,
    CustomerService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/customers", tags=["customers"])
CustomerReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "LOGISTICS_MANAGER")),
]
CustomerManager = Annotated[
    User,
    Depends(require_roles("LOGISTICS_MANAGER")),
]


def get_customer_service(db: Annotated[Session, Depends(get_db)]) -> CustomerService:
    return CustomerService(db)


@router.get(
    "",
    response_model=PageResponse[CustomerListRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_customers(
    pagination: Pagination,
    _current_user: CustomerReader,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> PageResponse[CustomerListRead]:
    result = service.list_customers(pagination)
    return to_page_response(
        result,
        (CustomerListRead.model_validate(customer) for customer in result.items),
    )


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 409, 422),
)
def create_customer(
    data: CustomerCreate,
    _current_user: CustomerManager,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> Customer | JSONResponse:
    try:
        return service.create_customer(data)
    except CustomerDocumentAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "CUSTOMER_DOCUMENT_ALREADY_EXISTS",
            "Já existe um cliente cadastrado com este documento.",
            [{"field": "document"}],
        )


@router.get(
    "/{customer_id}",
    response_model=CustomerRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_customer(
    customer_id: uuid.UUID,
    _current_user: CustomerReader,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> Customer | JSONResponse:
    try:
        return service.get_customer(customer_id)
    except CustomerNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "CUSTOMER_NOT_FOUND",
            "Cliente não encontrado.",
            [{"field": "id"}],
        )


@router.patch(
    "/{customer_id}",
    response_model=CustomerRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    _current_user: CustomerManager,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> Customer | JSONResponse:
    try:
        return service.update_customer(customer_id, data)
    except CustomerNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "CUSTOMER_NOT_FOUND",
            "Cliente não encontrado.",
            [{"field": "id"}],
        )
    except CustomerDocumentAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "CUSTOMER_DOCUMENT_ALREADY_EXISTS",
            "Já existe um cliente cadastrado com este documento.",
            [{"field": "document"}],
        )
