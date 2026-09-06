import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.pagination import PageResponse, Pagination, to_page_response
from app.core.responses import error_response, openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.drivers.models import Driver
from app.modules.drivers.schemas import (
    DriverCreate,
    DriverListRead,
    DriverRead,
    DriverUpdate,
)
from app.modules.drivers.service import (
    DriverDocumentAlreadyExistsError,
    DriverLicenseNumberAlreadyExistsError,
    DriverNotFoundError,
    DriverService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/drivers", tags=["drivers"])
DriverReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "LOGISTICS_MANAGER")),
]
DriverManager = Annotated[
    User,
    Depends(require_roles("LOGISTICS_MANAGER")),
]


def get_driver_service(db: Annotated[Session, Depends(get_db)]) -> DriverService:
    return DriverService(db)


@router.get(
    "",
    response_model=PageResponse[DriverListRead],
    responses=openapi_error_responses(401, 403, 422),
)
def list_drivers(
    pagination: Pagination,
    _current_user: DriverReader,
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> PageResponse[DriverListRead]:
    result = service.list_drivers(pagination)
    return to_page_response(
        result,
        (DriverListRead.model_validate(driver) for driver in result.items),
    )


@router.post(
    "",
    response_model=DriverRead,
    status_code=status.HTTP_201_CREATED,
    responses=openapi_error_responses(401, 403, 409, 422),
)
def create_driver(
    data: DriverCreate,
    _current_user: DriverManager,
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


@router.get(
    "/{driver_id}",
    response_model=DriverRead,
    responses=openapi_error_responses(401, 403, 404, 422),
)
def get_driver(
    driver_id: uuid.UUID,
    _current_user: DriverReader,
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


@router.patch(
    "/{driver_id}",
    response_model=DriverRead,
    responses=openapi_error_responses(401, 403, 404, 409, 422),
)
def update_driver(
    driver_id: uuid.UUID,
    data: DriverUpdate,
    _current_user: DriverManager,
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
