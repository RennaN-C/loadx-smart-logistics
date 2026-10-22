"""Operational discovery indexes for the OC93 central workspace."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResponse, PageResult, Pagination, to_page_response
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.access_profiles.catalog import Permission, has_permission
from app.modules.auth.dependencies import require_any_permission, require_permission
from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.schemas import DeliveryRead
from app.modules.drivers.service import DriverNotFoundError, DriverService
from app.modules.loading.models import LoadingSession
from app.modules.users.models import User

router = APIRouter(tags=["operations"])
Db = Annotated[Session, Depends(get_db)]
LoadingReader = Annotated[User, Depends(require_permission("loadx.loading.read"))]
DeliveryReader = Annotated[
    User, Depends(require_any_permission("loadx.deliveries.read", "loadx.trips.own"))
]
LoadingStatus = Literal["PENDING", "IN_PROGRESS", "FINISHED"]
DeliveryStatus = Literal["PENDING", "IN_DELIVERY", "DELIVERED", "CANCELED"]


class LoadingListRead(BaseModel):
    id: uuid.UUID
    load_plan_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/loading-sessions",
    response_model=PageResponse[LoadingListRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_loading_sessions(
    pagination: Pagination,
    _current_user: LoadingReader,
    db: Db,
    status: LoadingStatus | None = None,
) -> PageResponse[LoadingListRead]:
    direction = asc if pagination.sort_order == "asc" else desc
    filters = [LoadingSession.status == status] if status is not None else []
    total = db.scalar(select(func.count(LoadingSession.id)).where(*filters)) or 0
    rows = db.scalars(
        select(LoadingSession)
        .where(*filters)
        .order_by(direction(LoadingSession.id))
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    page = PageResult.create(rows, pagination, total)
    return to_page_response(
        page, (LoadingListRead.model_validate(row) for row in page.items)
    )


@router.get(
    "/deliveries",
    response_model=PageResponse[DeliveryRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_deliveries(
    pagination: Pagination,
    current_user: DeliveryReader,
    db: Db,
    status: DeliveryStatus | None = None,
) -> PageResponse[DeliveryRead]:
    if has_permission(current_user, Permission.DELIVERIES_READ):
        driver_id = None
    else:
        driver_id = current_user.driver_id
        if current_user.role != "DRIVER" or driver_id is None:
            raise ApiError(403, "AUTH_FORBIDDEN", "Acesso a entregas negado.")
        try:
            driver = DriverService(db).get_driver(driver_id)
        except DriverNotFoundError:
            raise ApiError(403, "AUTH_FORBIDDEN", "Motorista inexistente.") from None
        if not driver.active:
            raise ApiError(403, "AUTH_FORBIDDEN", "Motorista inativo.")

    direction = asc if pagination.sort_order == "asc" else desc
    filters = []
    if driver_id is not None:
        filters.append(Trip.driver_id == driver_id)
    if status is not None:
        filters.append(Delivery.status == status)
    total = (
        db.scalar(
            select(func.count(Delivery.id))
            .join(Trip, Trip.id == Delivery.trip_id)
            .where(*filters)
        )
        or 0
    )
    rows = db.scalars(
        select(Delivery)
        .join(Trip, Trip.id == Delivery.trip_id)
        .where(*filters)
        .order_by(direction(Trip.created_at), direction(Delivery.id))
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    page = PageResult.create(rows, pagination, total)
    return to_page_response(
        page, (DeliveryRead.model_validate(row) for row in page.items)
    )
