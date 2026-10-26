import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.status_history.schemas import AuditEntryRead
from app.modules.status_history.service import AuditInvalidPeriodError, AuditService
from app.modules.users.models import User

router = APIRouter(prefix="/audit", tags=["audit"])

AuditReader = Annotated[User, Depends(require_permission("loadx.audit.read"))]
AuditEntityType = Literal[
    "LOAD_DISTRIBUTION",
    "LOAD_DISTRIBUTION_PART",
    "ORDER",
    "LOAD_PLAN",
    "TRIP",
    "DELIVERY",
    "USER",
    "CUSTOMER",
    "CUSTOMER_ADDRESS",
    "REGISTRATION_IMPORT",
    "ATTACHMENT",
    "DRIVER_DOCUMENT",
    "DRIVER_DOCUMENT_POLICY",
    "DRIVER_DOCUMENT_TYPE",
    "TRUCK_DOCUMENT",
    "TRUCK_DOCUMENT_POLICY",
    "TRUCK_MAINTENANCE",
    "PRODUCT",
    "TRUCK",
    "DRIVER",
    "COMPANY_PROFILE",
    "ACCESS_PROFILE",
    "OUTBOX_EVENT",
]
AuditEventType = Literal[
    "STATUS_CHANGED",
    "OUTBOX_REPROCESSED",
    "PROFILE_CREATED",
    "PROFILE_UPDATED",
    "USER_CREATED",
    "USER_UPDATED",
    "COMPANY_PROFILE_CREATED",
    "COMPANY_PROFILE_UPDATED",
    "RECORD_ARCHIVED",
    "RECORD_REACTIVATED",
    "CUSTOMER_ADDRESS_CREATED",
    "CUSTOMER_ADDRESS_UPDATED",
    "CUSTOMER_ADDRESS_ARCHIVED",
    "CUSTOMER_ADDRESS_REACTIVATED",
    "MAINTENANCE_CREATED",
    "MAINTENANCE_CLOSED",
    "TRUCK_ODOMETER_UPDATED",
    "TRUCK_DOCUMENT_CREATED",
    "TRUCK_DOCUMENT_RENEWED",
    "TRUCK_DOCUMENT_POLICY_UPDATED",
    "DRIVER_DOCUMENT_CREATED",
    "DRIVER_DOCUMENT_RENEWED",
    "DRIVER_DOCUMENT_POLICY_UPDATED",
    "DRIVER_DOCUMENT_TYPE_APPROVED",
    "ATTACHMENT_REGISTERED",
    "ATTACHMENT_REVOKED",
    "IMPORT_COMPLETED",
    "IMPORT_REJECTED",
]


def get_audit_service(db: Annotated[Session, Depends(get_db)]) -> AuditService:
    return AuditService(db)


@router.get(
    "",
    response_model=PageResponse[AuditEntryRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_audit_entries(
    pagination: Pagination,
    current_user: AuditReader,
    service: Annotated[AuditService, Depends(get_audit_service)],
    entity_type: Annotated[AuditEntityType | None, Query()] = None,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    actor_id: Annotated[uuid.UUID | None, Query()] = None,
    event_type: Annotated[AuditEventType | None, Query()] = None,
    start_at: Annotated[datetime | None, Query()] = None,
    end_at: Annotated[datetime | None, Query()] = None,
) -> PageResponse[AuditEntryRead] | JSONResponse:
    if current_user.role != "ADMIN" and (
        entity_type in {"COMPANY_PROFILE", "ACCESS_PROFILE", "OUTBOX_EVENT"}
        or event_type
        in {
            "OUTBOX_REPROCESSED",
            "COMPANY_PROFILE_CREATED",
            "COMPANY_PROFILE_UPDATED",
            "PROFILE_CREATED",
            "PROFILE_UPDATED",
        }
    ):
        return error_response(
            403, "AUTH_FORBIDDEN", "Acesso restrito ao administrador."
        )
    try:
        result = service.list_entries(
            pagination,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            event_type=event_type,
            start_at=start_at,
            end_at=end_at,
            exclude_company=current_user.role != "ADMIN",
        )
    except AuditInvalidPeriodError:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "AUDIT_INVALID_PERIOD",
            "O período informado para a auditoria é inválido.",
            [{"field": "start_at"}, {"field": "end_at"}],
        )

    return to_page_response(
        result,
        (AuditEntryRead.model_validate(item) for item in result.items),
    )
