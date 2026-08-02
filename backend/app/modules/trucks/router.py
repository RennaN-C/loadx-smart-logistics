import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.trucks.models import Truck
from app.modules.trucks.schemas import TruckCreate, TruckRead, TruckUpdate
from app.modules.trucks.service import (
    TruckNotFoundError,
    TruckPlateAlreadyExistsError,
    TruckService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/trucks", tags=["trucks"])
TruckReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "CHECKER", "LOGISTICS_MANAGER")),
]
TruckManager = Annotated[
    User,
    Depends(require_roles("LOGISTICS_MANAGER")),
]


def get_truck_service(db: Annotated[Session, Depends(get_db)]) -> TruckService:
    return TruckService(db)


@router.get(
    "",
    response_model=list[TruckRead],
    responses=openapi_error_responses(401, 403),
)
def list_trucks(
    _current_user: TruckReader,
    service: Annotated[TruckService, Depends(get_truck_service)],
) -> list[Truck]:
    return list(service.list_trucks())


@router.post(
    "",
    response_model=TruckRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 409, 422),
)
def create_truck(
    data: TruckCreate,
    _current_user: TruckManager,
    service: Annotated[TruckService, Depends(get_truck_service)],
) -> Truck | JSONResponse:
    try:
        return service.create_truck(data)
    except TruckPlateAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRUCK_PLATE_ALREADY_EXISTS",
            "Já existe um caminhão cadastrado com esta placa.",
            [{"field": "plate"}],
        )


@router.get(
    "/{truck_id}",
    response_model=TruckRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_truck(
    truck_id: uuid.UUID,
    _current_user: TruckReader,
    service: Annotated[TruckService, Depends(get_truck_service)],
) -> Truck | JSONResponse:
    try:
        return service.get_truck(truck_id)
    except TruckNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "TRUCK_NOT_FOUND",
            "Caminhão não encontrado.",
            [{"field": "id"}],
        )


@router.patch(
    "/{truck_id}",
    response_model=TruckRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def update_truck(
    truck_id: uuid.UUID,
    data: TruckUpdate,
    _current_user: TruckManager,
    service: Annotated[TruckService, Depends(get_truck_service)],
) -> Truck | JSONResponse:
    try:
        return service.update_truck(truck_id, data)
    except TruckNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "TRUCK_NOT_FOUND",
            "Caminhão não encontrado.",
            [{"field": "id"}],
        )
    except TruckPlateAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "TRUCK_PLATE_ALREADY_EXISTS",
            "Já existe um caminhão cadastrado com esta placa.",
            [{"field": "plate"}],
        )
