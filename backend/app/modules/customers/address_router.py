import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.customers.address_schemas import (
    CustomerAddressCreate,
    CustomerAddressRead,
    CustomerAddressUpdate,
)
from app.modules.customers.address_service import CustomerAddressService
from app.modules.customers.models import CustomerAddress
from app.modules.customers.router import CustomerManager, CustomerReader
from app.shared.record_lifecycle import ArchiveFilter, active_filter

router = APIRouter(
    prefix="/customers/{customer_id}/addresses",
    tags=["customer-addresses"],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)


def get_customer_address_service(
    db: Annotated[Session, Depends(get_db)],
) -> CustomerAddressService:
    return CustomerAddressService(db)


Service = Annotated[CustomerAddressService, Depends(get_customer_address_service)]


@router.get("", response_model=PageResponse[CustomerAddressRead])
def list_addresses(
    customer_id: uuid.UUID,
    pagination: Pagination,
    _user: CustomerReader,
    service: Service,
    archive_status: ArchiveFilter = "active",
) -> PageResponse[CustomerAddressRead]:
    result = service.list_addresses(
        customer_id, pagination, active=active_filter(archive_status)
    )
    return to_page_response(
        result, (CustomerAddressRead.model_validate(row) for row in result.items)
    )


@router.post("", response_model=CustomerAddressRead, status_code=201)
def create_address(
    customer_id: uuid.UUID,
    data: CustomerAddressCreate,
    _user: CustomerManager,
    service: Service,
) -> CustomerAddress:
    return service.create_address(customer_id, data, changed_by=_user.id)


@router.patch("/{address_id}", response_model=CustomerAddressRead)
def update_address(
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    data: CustomerAddressUpdate,
    _user: CustomerManager,
    service: Service,
) -> CustomerAddress:
    return service.update_address(customer_id, address_id, data, changed_by=_user.id)
