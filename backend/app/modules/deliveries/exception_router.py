"""Append-only OC94 delivery exception endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_any_permission
from app.modules.deliveries.exception_schemas import (
    DeliveryExceptionCreate,
    DeliveryExceptionRead,
)
from app.modules.deliveries.exception_service import DeliveryExceptionService
from app.modules.users.models import User

router = APIRouter(tags=["deliveries"])
Reader = Annotated[
    User, Depends(require_any_permission("loadx.deliveries.read", "loadx.trips.own"))
]
Operator = Annotated[
    User, Depends(require_any_permission("loadx.deliveries.manage", "loadx.trips.own"))
]
Db = Annotated[Session, Depends(get_db)]


@router.get(
    "/deliveries/{delivery_id}/exceptions",
    response_model=list[DeliveryExceptionRead],
    responses=openapi_error_responses(401, 403, 404),
)
def list_delivery_exceptions(
    delivery_id: uuid.UUID, current_user: Reader, db: Db
) -> list[DeliveryExceptionRead]:
    return DeliveryExceptionService(db).list_for_delivery(
        delivery_id, current_user=current_user
    )


@router.post(
    "/deliveries/{delivery_id}/exceptions",
    response_model=DeliveryExceptionRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def record_delivery_exception(
    delivery_id: uuid.UUID,
    data: DeliveryExceptionCreate,
    response: Response,
    current_user: Operator,
    db: Db,
) -> DeliveryExceptionRead:
    result, created = DeliveryExceptionService(db).register(
        delivery_id, data, current_user=current_user
    )
    response.status_code = 201 if created else 200
    return result
