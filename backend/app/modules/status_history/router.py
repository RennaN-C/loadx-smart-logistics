import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.status_history.schemas import AuditEntryRead
from app.modules.status_history.service import AuditInvalidPeriodError, AuditService
from app.modules.users.models import User

router = APIRouter(prefix="/audit", tags=["audit"])

AuditReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "LOGISTICS_MANAGER")),
]
AuditEntityType = Literal["ORDER", "LOAD_PLAN", "TRIP", "DELIVERY", "USER"]
AuditEventType = Literal["STATUS_CHANGED", "USER_CREATED", "USER_UPDATED"]


def get_audit_service(db: Annotated[Session, Depends(get_db)]) -> AuditService:
    return AuditService(db)


@router.get(
    "",
    response_model=PageResponse[AuditEntryRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_audit_entries(
    pagination: Pagination,
    _current_user: AuditReader,
    service: Annotated[AuditService, Depends(get_audit_service)],
    entity_type: Annotated[AuditEntityType | None, Query()] = None,
    entity_id: Annotated[uuid.UUID | None, Query()] = None,
    actor_id: Annotated[uuid.UUID | None, Query()] = None,
    event_type: Annotated[AuditEventType | None, Query()] = None,
    start_at: Annotated[datetime | None, Query()] = None,
    end_at: Annotated[datetime | None, Query()] = None,
) -> PageResponse[AuditEntryRead] | JSONResponse:
    try:
        result = service.list_entries(
            pagination,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            event_type=event_type,
            start_at=start_at,
            end_at=end_at,
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
