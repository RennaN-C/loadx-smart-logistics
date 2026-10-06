import logging
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.router import api_router
from app.core.config import Settings, settings
from app.core.exceptions import ApiError, register_exception_handlers
from app.core.http_security import OriginValidationMiddleware, SecurityHeadersMiddleware
from app.core.observability import (
    OperationalContextMiddleware,
    OperationalEvent,
    configure_observability,
    emit_operational_event,
)
from app.core.responses import openapi_error_responses
from app.database.readiness import DatabaseReadinessChecker, ReadinessCheckError


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    service: Literal["loadx-api"]


def get_readiness_checker(request: Request) -> DatabaseReadinessChecker:
    checker: DatabaseReadinessChecker = request.app.state.readiness_checker
    return checker


def create_app(app_settings: Settings | None = None) -> FastAPI:
    current_settings = app_settings or settings
    configure_observability(current_settings.operational_log_level)

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        emit_operational_event(OperationalEvent.APP_STARTED)
        try:
            yield
        finally:
            emit_operational_event(OperationalEvent.APP_STOPPED)

    expose_api_docs = current_settings.app_env == "local"
    application = FastAPI(
        title="LoadX API",
        version="1.0.0",
        docs_url="/docs" if expose_api_docs else None,
        redoc_url="/redoc" if expose_api_docs else None,
        openapi_url="/openapi.json" if expose_api_docs else None,
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    application.state.readiness_checker = DatabaseReadinessChecker(
        current_settings.database_url
    )

    application.add_middleware(
        OriginValidationMiddleware,
        allowed_origins=current_settings.backend_cors_origins,
    )
    application.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=current_settings.app_env == "production",
    )
    application.add_middleware(
        OperationalContextMiddleware,
        log_requests=current_settings.operational_request_logs,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
        expose_headers=["X-CSRF-Token"],
    )

    application.include_router(api_router, prefix="/api/v1")

    @application.get(
        "/health",
        tags=["health"],
        responses=openapi_error_responses(500),
    )
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "loadx-api"}

    @application.get(
        "/ready",
        tags=["health"],
        response_model=ReadinessResponse,
        responses=openapi_error_responses(500, 503),
    )
    def readiness(
        checker: Annotated[
            DatabaseReadinessChecker,
            Depends(get_readiness_checker),
        ],
    ) -> ReadinessResponse:
        try:
            checker.check()
        except ReadinessCheckError as error:
            emit_operational_event(
                OperationalEvent.READINESS_FAILED,
                level=logging.WARNING,
                alert=True,
                reason=error.reason.value,
            )
            raise ApiError(
                status_code=503,
                code="SERVICE_NOT_READY",
                message="O serviço não está pronto.",
            ) from None
        return ReadinessResponse(status="ready", service="loadx-api")

    return application


app = create_app()
