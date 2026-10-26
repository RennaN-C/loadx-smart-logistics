import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.pagination import Pagination
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.notifications.inbox_service import InboxService
from app.modules.notifications.schemas import (
    Category,
    EventType,
    NotificationPage,
    NotificationRead,
    NotificationSource,
    PreferencesRead,
    PreferencesWrite,
    ReadAllResult,
    UnreadCount,
)
from app.modules.users.models import User

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    responses=openapi_error_responses(401, 403, 422),
)
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_inbox_service(db: Annotated[Session, Depends(get_db)]) -> InboxService:
    return InboxService(db)


Inbox = Annotated[InboxService, Depends(get_inbox_service)]


@router.get("")
def list_notifications(
    pagination: Pagination,
    current_user: CurrentUser,
    service: Inbox,
    event_type: Annotated[EventType | None, Query()] = None,
    category: Annotated[Category | None, Query()] = None,
    read: Annotated[bool | None, Query()] = None,
) -> NotificationPage:
    return service.list_notifications(
        current_user, pagination, event_type=event_type, category=category, read=read
    )


@router.get("/unread-count")
def unread_count(current_user: CurrentUser, service: Inbox) -> UnreadCount:
    return UnreadCount(unread_count=service.unread_count(current_user))


@router.get("/preferences")
def get_preferences(current_user: CurrentUser, service: Inbox) -> PreferencesRead:
    return service.preferences(current_user)


@router.put("/preferences")
def save_preferences(
    data: PreferencesWrite, current_user: CurrentUser, service: Inbox
) -> PreferencesRead:
    return service.save_preferences(current_user, data)


@router.post("/read-all")
def mark_all_read(current_user: CurrentUser, service: Inbox) -> ReadAllResult:
    return ReadAllResult(updated=service.mark_all_read(current_user))


@router.post(
    "/{notification_id}/read",
    responses=openapi_error_responses(404),
)
def mark_read(
    notification_id: uuid.UUID, current_user: CurrentUser, service: Inbox
) -> NotificationRead:
    return service.mark_read(current_user, notification_id)


@router.get(
    "/{notification_id}/source",
    responses=openapi_error_responses(404),
)
def source(
    notification_id: uuid.UUID, current_user: CurrentUser, service: Inbox
) -> NotificationSource:
    return NotificationSource(href=service.source(current_user, notification_id))
