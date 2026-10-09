import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.trucks.document_schemas import (
    DocumentCreate,
    DocumentKind,
    DocumentRead,
    PolicyRead,
    PolicyUpdate,
    document_status,
)
from app.modules.trucks.document_service import DocumentService
from app.modules.trucks.models import TruckDocument
from app.modules.trucks.router import TruckManager, TruckReader
from app.modules.trucks.service import TruckNotFoundError

router = APIRouter(
    prefix="/trucks/{truck_id}",
    tags=["truck-documents"],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)


def get_service(db: Annotated[Session, Depends(get_db)]) -> DocumentService:
    return DocumentService(db)


Service = Annotated[DocumentService, Depends(get_service)]


def read_document(record: TruckDocument) -> DocumentRead:
    return DocumentRead(
        **{
            field: getattr(record, field)
            for field in DocumentRead.model_fields
            if field != "status"
        },
        status=document_status(record),
    )


def truck_error(error: TruckNotFoundError) -> ApiError:
    return ApiError(404, "TRUCK_NOT_FOUND", "Caminhão não encontrado.")


@router.get("/documents")
def list_documents(
    truck_id: uuid.UUID, pagination: Pagination, _user: TruckReader, service: Service
) -> PageResponse[DocumentRead]:
    try:
        result = service.list(truck_id, pagination)
        return to_page_response(result, (read_document(row) for row in result.items))
    except TruckNotFoundError as error:
        raise truck_error(error) from error


@router.post("/documents", status_code=201)
def create_document(
    truck_id: uuid.UUID, data: DocumentCreate, _user: TruckManager, service: Service
) -> DocumentRead:
    try:
        return read_document(service.create(truck_id, data, actor=_user.id))
    except TruckNotFoundError as error:
        raise truck_error(error) from error


@router.post("/documents/{document_id}/renew", status_code=201)
def renew_document(
    truck_id: uuid.UUID,
    document_id: uuid.UUID,
    data: DocumentCreate,
    _user: TruckManager,
    service: Service,
) -> DocumentRead:
    try:
        return read_document(
            service.create(truck_id, data, actor=_user.id, replacing=document_id)
        )
    except TruckNotFoundError as error:
        raise truck_error(error) from error


@router.get("/document-policies")
def list_policies(
    truck_id: uuid.UUID, _user: TruckReader, service: Service
) -> list[PolicyRead]:
    try:
        return [PolicyRead.model_validate(row) for row in service.policies(truck_id)]
    except TruckNotFoundError as error:
        raise truck_error(error) from error


@router.patch("/document-policies/{kind}")
def update_policy(
    truck_id: uuid.UUID,
    kind: DocumentKind,
    data: PolicyUpdate,
    _user: TruckManager,
    service: Service,
) -> PolicyRead:
    try:
        return PolicyRead.model_validate(
            service.update_policy(truck_id, kind, data, actor=_user.id)
        )
    except TruckNotFoundError as error:
        raise truck_error(error) from error
