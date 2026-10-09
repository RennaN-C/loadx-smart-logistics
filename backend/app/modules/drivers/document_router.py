import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.drivers.document_schemas import (
    DriverDocumentCreate,
    DriverDocumentPolicyRead,
    DriverDocumentPolicyUpdate,
    DriverDocumentRead,
    DriverDocumentTypeCreate,
    DriverDocumentTypeRead,
)
from app.modules.drivers.document_service import DocumentService
from app.modules.drivers.models import DriverDocument
from app.modules.drivers.router import DriverManager, DriverReader
from app.modules.drivers.service import DriverNotFoundError
from app.shared.document_validity import document_status

router = APIRouter(
    prefix="/drivers/{driver_id}",
    tags=["driver-documents"],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)


def get_service(db: Annotated[Session, Depends(get_db)]) -> DocumentService:
    return DocumentService(db)


Service = Annotated[DocumentService, Depends(get_service)]


def read_document(record: DriverDocument) -> DriverDocumentRead:
    return DriverDocumentRead(
        **{
            field: getattr(record, field)
            for field in DriverDocumentRead.model_fields
            if field != "status"
        },
        status=document_status(record),
    )


def driver_error() -> ApiError:
    return ApiError(404, "TRUCK_NOT_FOUND", "Motorista não encontrado.")


@router.get("/documents")
def list_documents(
    driver_id: uuid.UUID, pagination: Pagination, _user: DriverReader, service: Service
) -> PageResponse[DriverDocumentRead]:
    try:
        result = service.list_documents(driver_id, pagination)
        return to_page_response(result, (read_document(row) for row in result.items))
    except DriverNotFoundError as error:
        raise driver_error() from error


@router.post("/documents", status_code=201)
def create_document(
    driver_id: uuid.UUID,
    data: DriverDocumentCreate,
    _user: DriverManager,
    service: Service,
) -> DriverDocumentRead:
    try:
        return read_document(service.create(driver_id, data, actor=_user.id))
    except DriverNotFoundError as error:
        raise driver_error() from error


@router.post("/documents/{document_id}/renew", status_code=201)
def renew_document(
    driver_id: uuid.UUID,
    document_id: uuid.UUID,
    data: DriverDocumentCreate,
    _user: DriverManager,
    service: Service,
) -> DriverDocumentRead:
    try:
        return read_document(
            service.create(driver_id, data, actor=_user.id, replacing=document_id)
        )
    except DriverNotFoundError as error:
        raise driver_error() from error


@router.get("/document-policies")
def list_policies(
    driver_id: uuid.UUID, _user: DriverReader, service: Service
) -> list[DriverDocumentPolicyRead]:
    try:
        return [
            DriverDocumentPolicyRead.model_validate(row)
            for row in service.policies(driver_id)
        ]
    except DriverNotFoundError as error:
        raise driver_error() from error


@router.patch("/document-policies/{document_type_id}")
def update_policy(
    driver_id: uuid.UUID,
    document_type_id: uuid.UUID,
    data: DriverDocumentPolicyUpdate,
    _user: DriverManager,
    service: Service,
) -> DriverDocumentPolicyRead:
    try:
        return DriverDocumentPolicyRead.model_validate(
            service.update_policy(driver_id, document_type_id, data, actor=_user.id)
        )
    except DriverNotFoundError as error:
        raise driver_error() from error


type_router = APIRouter(
    prefix="/driver-document-types",
    tags=["driver-documents"],
    responses=openapi_error_responses(401, 403, 409, 422),
)


@type_router.get("")
def list_document_types(
    _user: DriverReader, service: Service
) -> list[DriverDocumentTypeRead]:
    return [DriverDocumentTypeRead.model_validate(row) for row in service.types()]


@type_router.post("", status_code=201)
def approve_document_type(
    data: DriverDocumentTypeCreate, _user: DriverManager, service: Service
) -> DriverDocumentTypeRead:
    return DriverDocumentTypeRead.model_validate(
        service.approve_type(data, actor=_user.id)
    )
