import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_any_permission
from app.modules.notifications.communication_schemas import DeliveryCommunicationRead
from app.modules.notifications.communication_service import DeliveryCommunicationService
from app.modules.users.models import User

router = APIRouter(
    tags=["deliveries"], responses=openapi_error_responses(401, 403, 404, 422)
)
Reader = Annotated[
    User, Depends(require_any_permission("loadx.deliveries.read", "loadx.trips.own"))
]


@router.get("/deliveries/{delivery_id}/communications")
def list_delivery_communications(
    delivery_id: uuid.UUID,
    pagination: Pagination,
    current_user: Reader,
    db: Annotated[Session, Depends(get_db)],
) -> PageResponse[DeliveryCommunicationRead]:
    return DeliveryCommunicationService(db).list_for_delivery(
        delivery_id, current_user, pagination
    )
