import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.observability import request_id_context
from app.core.responses import openapi_error_responses
from app.modules.auth.dependencies import require_roles
from app.modules.integration_health.schemas import IntegrationHealthReport
from app.modules.integration_health.service import IntegrationHealthService
from app.modules.users.models import User

router = APIRouter(
    prefix="/integration-health",
    tags=["integration-health"],
    responses=openapi_error_responses(401, 403, 422),
)


def get_service(request: Request) -> IntegrationHealthService:
    return IntegrationHealthService(
        request.app.state.readiness_checker,
        ai_provider=request.app.state.integration_health_settings.ai_provider,
        sources=request.app.state.integration_health_sources,
    )


@router.get("")
async def read_integration_health(
    _admin: Annotated[User, Depends(require_roles("ADMIN"))],
    service: Annotated[IntegrationHealthService, Depends(get_service)],
) -> IntegrationHealthReport:
    return await service.report(
        uuid.UUID(request_id_context.get())
        if request_id_context.get()
        else uuid.uuid4()
    )
