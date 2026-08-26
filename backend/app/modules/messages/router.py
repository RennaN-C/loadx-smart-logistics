from fastapi import APIRouter

from app.core.responses import openapi_error_responses
from app.modules.messages.schemas import MessageInterpretRequest, MessageInterpretResponse
from app.modules.messages.service import MessageInterpreterService

router = APIRouter(prefix="/messages", tags=["messages"])
service = MessageInterpreterService()


@router.post(
    "/interpret",
    response_model=MessageInterpretResponse,
    responses=openapi_error_responses(422),
)
def interpret_message(payload: MessageInterpretRequest) -> MessageInterpretResponse:
    return service.interpret_message(payload.message)
