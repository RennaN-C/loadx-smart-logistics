import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.trucks.maintenance_schemas import (
    MaintenanceClose,
    MaintenanceCreate,
    MaintenanceRead,
)
from app.modules.trucks.maintenance_service import MaintenanceService
from app.modules.trucks.router import TruckManager, TruckReader
from app.modules.trucks.service import TruckNotFoundError

router = APIRouter(
    prefix="/trucks/{truck_id}/maintenances",
    tags=["truck-maintenances"],
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)


def get_service(db: Annotated[Session, Depends(get_db)]) -> MaintenanceService:
    return MaintenanceService(db)


Service = Annotated[MaintenanceService, Depends(get_service)]


@router.get("", response_model=PageResponse[MaintenanceRead])
def list_maintenances(
    truck_id: uuid.UUID, pagination: Pagination, _user: TruckReader, service: Service
) -> PageResponse[MaintenanceRead]:
    try:
        result = service.list(truck_id, pagination)
    except TruckNotFoundError as error:
        raise ApiError(404, "TRUCK_NOT_FOUND", "Caminhão não encontrado.") from error
    return to_page_response(
        result, (MaintenanceRead.model_validate(row) for row in result.items)
    )


@router.post("", response_model=MaintenanceRead, status_code=201)
def create_maintenance(
    truck_id: uuid.UUID, data: MaintenanceCreate, _user: TruckManager, service: Service
) -> MaintenanceRead:
    try:
        return MaintenanceRead.model_validate(
            service.create(truck_id, data, actor=_user.id)
        )
    except TruckNotFoundError as error:
        raise ApiError(404, "TRUCK_NOT_FOUND", "Caminhão não encontrado.") from error


@router.post("/{maintenance_id}/close", response_model=MaintenanceRead)
def close_maintenance(
    truck_id: uuid.UUID,
    maintenance_id: uuid.UUID,
    data: MaintenanceClose,
    _user: TruckManager,
    service: Service,
) -> MaintenanceRead:
    try:
        return MaintenanceRead.model_validate(
            service.close(truck_id, maintenance_id, data, actor=_user.id)
        )
    except TruckNotFoundError as error:
        raise ApiError(404, "TRUCK_NOT_FOUND", "Caminhão não encontrado.") from error
