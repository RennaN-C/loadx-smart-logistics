from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.integrations.whatsapp import WhatsAppProvider, get_whatsapp_provider
from app.modules.auth.dependencies import require_roles
from app.modules.messages.schemas import (
    MessageInterpretRequest,
    MessageInterpretResponse,
)
from app.modules.messages.service import ControlledMessageService
from app.modules.users.models import User

router = APIRouter(prefix="/messages", tags=["messages"])
MessageSimulatorUser = Annotated[
    User, Depends(require_roles("ADMIN", "LOGISTICS_MANAGER"))
]


def get_message_service(
    db: Annotated[Session, Depends(get_db)],
    provider: Annotated[WhatsAppProvider, Depends(get_whatsapp_provider)],
) -> ControlledMessageService:
    return ControlledMessageService(db, provider)


@router.post(
    "/interpret",
    responses=openapi_error_responses(401, 403, 422),
)
def interpret_message(
    payload: MessageInterpretRequest,
    _current_user: MessageSimulatorUser,
    service: Annotated[ControlledMessageService, Depends(get_message_service)],
) -> MessageInterpretResponse:
    return service.process(payload.driver_phone, payload.message)
