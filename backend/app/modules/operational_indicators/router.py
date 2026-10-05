from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.operational_indicators.schemas import OperationalIndicatorsRead
from app.modules.operational_indicators.service import OperationalIndicatorsService
from app.modules.users.models import User

router = APIRouter(
    prefix="/operational-indicators",
    tags=["operational-indicators"],
)

OperationalIndicatorsReader = Annotated[
    User,
    Depends(require_roles("ADMIN", "LOGISTICS_MANAGER")),
]


def get_operational_indicators_service(
    db: Annotated[Session, Depends(get_db)],
) -> OperationalIndicatorsService:
    return OperationalIndicatorsService(db)


@router.get(
    "",
    response_model=OperationalIndicatorsRead,
    responses=openapi_error_responses(401, 403),
)
def get_operational_indicators(
    _current_user: OperationalIndicatorsReader,
    service: Annotated[
        OperationalIndicatorsService,
        Depends(get_operational_indicators_service),
    ],
) -> OperationalIndicatorsRead:
    return OperationalIndicatorsRead.model_validate(service.get_indicators())
