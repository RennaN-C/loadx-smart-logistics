from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.responses import openapi_error_responses
from app.database.session import get_db
from app.modules.assistant.schemas import ChatRequest, ChatResponse
from app.modules.assistant.service import AssistantService
from app.modules.auth.dependencies import require_roles
from app.modules.users.models import User

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_service(db: Annotated[Session, Depends(get_db)]) -> AssistantService:
    return AssistantService(db, settings)


@router.post(
    "/messages",
    response_model=ChatResponse,
    responses=openapi_error_responses(401, 403, 404, 422, 429),
)
def chat(
    data: ChatRequest,
    user: Annotated[
        User, Depends(require_roles("ADMIN", "LOGISTICS_MANAGER", "CHECKER"))
    ],
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> ChatResponse:
    return service.chat(user, data)
