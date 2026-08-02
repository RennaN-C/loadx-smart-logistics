import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.responses import error_response
from app.database.session import get_db
from app.modules.customers.models import Customer
from app.modules.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from app.modules.customers.service import (
    CustomerDocumentAlreadyExistsError,
    CustomerNotFoundError,
    CustomerService,
)

router = APIRouter(prefix="/customers", tags=["customers"])


def get_customer_service(db: Annotated[Session, Depends(get_db)]) -> CustomerService:
    return CustomerService(db)


@router.get("", response_model=list[CustomerRead])
def list_customers(
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> list[Customer]:
    return list(service.list_customers())


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
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


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: uuid.UUID,
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


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
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
