"""Read-only day/week activity calendar; scheduling is a later phase."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_any_permission
from app.modules.operational_agenda.schemas import AgendaKind, OperationalAgendaRead
from app.modules.operational_agenda.service import (
    AgendaFilters,
    OperationalAgendaService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/operations", tags=["operations"])
Reader = Annotated[
    User, Depends(require_any_permission("loadx.trips.read", "loadx.trips.own"))
]
Db = Annotated[Session, Depends(get_db)]


@router.get(
    "/agenda",
    response_model=OperationalAgendaRead,
    responses=openapi_error_responses(401, 403, 409, 422),
)
def operational_agenda(
    start: datetime,
    end: datetime,
    current_user: Reader,
    db: Db,
    kind: AgendaKind | None = None,
    truck_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
) -> OperationalAgendaRead:
    return OperationalAgendaService(db).get(
        AgendaFilters(start, end, kind, truck_id, driver_id),
        current_user=current_user,
    )
