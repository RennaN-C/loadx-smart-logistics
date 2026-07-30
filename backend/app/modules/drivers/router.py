import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.drivers.models import Driver
from app.modules.drivers.schemas import DriverCreate, DriverRead, DriverUpdate
from app.modules.drivers.service import (
    DriverDocumentAlreadyExistsError,
    DriverLicenseNumberAlreadyExistsError,
    DriverNotFoundError,
    DriverService,
)

router = APIRouter(prefix="/drivers", tags=["drivers"])


def get_driver_service(db: Annotated[Session, Depends(get_db)]) -> DriverService:
    return DriverService(db)


def error_response(status_code: int, code: str, message: str, details: list[Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or [],
        },
    )


@router.get("", response_model=list[DriverRead])
def list_drivers(service: Annotated[DriverService, Depends(get_driver_service)]) -> list[Driver]:
    return list(service.list_drivers())


@router.post("", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
def create_driver(
    data: DriverCreate,
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> Driver | JSONResponse:
    try:
        return service.create_driver(data)
    except DriverDocumentAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "DRIVER_DOCUMENT_ALREADY_EXISTS",
            "Já existe um motorista cadastrado com este documento.",
            [{"field": "document"}],
        )
    except DriverLicenseNumberAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "DRIVER_LICENSE_NUMBER_ALREADY_EXISTS",
            "Já existe um motorista cadastrado com esta CNH.",
            [{"field": "license_number"}],
        )


@router.get("/{driver_id}", response_model=DriverRead)
def get_driver(
    driver_id: uuid.UUID,
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> Driver | JSONResponse:
    try:
        return service.get_driver(driver_id)
    except DriverNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "DRIVER_NOT_FOUND",
            "Motorista não encontrado.",
            [{"field": "id"}],
        )


@router.patch("/{driver_id}", response_model=DriverRead)
def update_driver(
    driver_id: uuid.UUID,
    data: DriverUpdate,
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> Driver | JSONResponse:
    try:
        return service.update_driver(driver_id, data)
    except DriverNotFoundError:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "DRIVER_NOT_FOUND",
            "Motorista não encontrado.",
            [{"field": "id"}],
        )
    except DriverDocumentAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "DRIVER_DOCUMENT_ALREADY_EXISTS",
            "Já existe um motorista cadastrado com este documento.",
            [{"field": "document"}],
        )
    except DriverLicenseNumberAlreadyExistsError:
        return error_response(
            status.HTTP_409_CONFLICT,
            "DRIVER_LICENSE_NUMBER_ALREADY_EXISTS",
            "Já existe um motorista cadastrado com esta CNH.",
            [{"field": "license_number"}],
        )
