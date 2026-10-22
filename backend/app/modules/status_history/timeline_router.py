"""Timeline for existing trips. No duplicate audit records are written."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.responses import openapi_error_responses
from app.modules.deliveries.service import TripAccessForbiddenError, TripNotFoundError
from app.database.session import get_db
from app.modules.auth.dependencies import require_any_permission
from app.modules.status_history.timeline_schemas import TimelinePage
from app.modules.status_history.timeline_service import OperationalTimelineService
from app.modules.users.models import User

router = APIRouter(tags=["status-history"])
Reader = Annotated[
    User, Depends(require_any_permission("loadx.trips.read", "loadx.trips.own"))
]
Db = Annotated[Session, Depends(get_db)]


@router.get(
    "/trips/{trip_id}/timeline",
    response_model=TimelinePage,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def get_trip_timeline(
    trip_id: uuid.UUID,
    current_user: Reader,
    db: Db,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TimelinePage:
    try:
        return OperationalTimelineService(db).list_trip(
            trip_id, current_user=current_user, page=page, page_size=page_size
        )
    except TripNotFoundError:
        raise ApiError(404, "TRIP_NOT_FOUND", "Viagem nao encontrada.") from None
    except TripAccessForbiddenError:
        raise ApiError(403, "AUTH_FORBIDDEN", "Acesso negado a esta viagem.") from None
