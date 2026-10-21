import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.notifications.outbox_schemas import (
    AttemptRead,
    EventRead,
    EventSource,
    QueueSummary,
    RetryRequest,
    State,
)
from app.modules.notifications.outbox_service import OutboxService
from app.modules.notifications.schemas import EventType
from app.modules.users.models import User

router = APIRouter(
    prefix="/outbox-events",
    tags=["outbox-events"],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
Admin = Annotated[User, Depends(require_roles("ADMIN"))]


def get_service(db: Annotated[Session, Depends(get_db)]) -> OutboxService:
    return OutboxService(db)


Service = Annotated[OutboxService, Depends(get_service)]


@router.get("")
def list_events(
    pagination: Pagination,
    _admin: Admin,
    service: Service,
    status: Annotated[State | None, Query()] = None,
    event_type: Annotated[EventType | None, Query()] = None,
) -> PageResponse[EventRead]:
    return service.list_events(pagination, status=status, event_type=event_type)


@router.get("/summary")
def summary(_admin: Admin, service: Service) -> QueueSummary:
    return service.summary()


@router.get("/{event_id}")
def detail(event_id: uuid.UUID, _admin: Admin, service: Service) -> EventRead:
    return service.detail(event_id)


@router.get("/{event_id}/attempts")
def attempts(
    event_id: uuid.UUID, pagination: Pagination, _admin: Admin, service: Service
) -> PageResponse[AttemptRead]:
    return service.attempts(event_id, pagination)


@router.get("/{event_id}/source")
def source(event_id: uuid.UUID, admin: Admin, service: Service) -> EventSource:
    return EventSource(href=service.source(event_id, admin))


@router.post("/{event_id}/retry")
def retry(
    event_id: uuid.UUID, data: RetryRequest, admin: Admin, service: Service
) -> EventRead:
    return service.retry(event_id, data.command_id, admin)
