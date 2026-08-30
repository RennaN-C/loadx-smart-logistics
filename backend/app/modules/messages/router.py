from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.integrations.whatsapp.provider import MockWhatsAppProvider
from app.modules.messages.schemas import (
    MessageInterpretRequest,
    MessageInterpretResponse,
)
from app.modules.messages.service import ControlledMessageService

router = APIRouter(prefix="/messages", tags=["messages"])
mock_provider = MockWhatsAppProvider()


def get_message_service(
    db: Annotated[Session, Depends(get_db)],
) -> ControlledMessageService:
    return ControlledMessageService(db, mock_provider)


@router.post(
    "/interpret",
    response_model=MessageInterpretResponse,
    responses=openapi_error_responses(422),
)
def interpret_message(
    payload: MessageInterpretRequest,
    service: Annotated[ControlledMessageService, Depends(get_message_service)],
) -> MessageInterpretResponse:
    return service.process(payload.driver_phone, payload.message)
