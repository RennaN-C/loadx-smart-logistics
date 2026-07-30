import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.trucks.models import Truck
from app.modules.trucks.schemas import TruckCreate, TruckRead, TruckUpdate
from app.modules.trucks.service import (
    TruckNotFoundError,
    TruckPlateAlreadyExistsError,
    TruckService,
)

router = APIRouter(prefix="/trucks", tags=["trucks"])


def get_truck_service(db: Annotated[Session, Depends(get_db)]) -> TruckService:
    return TruckService(db)


def error_response(status_code: int, code: str, message: str, details: list[Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or [],
        },
    )


@router.get("", response_model=list[TruckRead])
def list_trucks(service: Annotated[TruckService, Depends(get_truck_service)]) -> list[Truck]:
    return list(service.list_trucks())


@router.post("", response_model=TruckRead, status_code=status.HTTP_201_CREATED)
def create_truck(
    data: TruckCreate,
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


@router.get("/{truck_id}", response_model=TruckRead)
def get_truck(
    truck_id: uuid.UUID,
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


@router.patch("/{truck_id}", response_model=TruckRead)
def update_truck(
    truck_id: uuid.UUID,
    data: TruckUpdate,
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
