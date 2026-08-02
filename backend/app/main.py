from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, settings
from app.core.exceptions import register_exception_handlers
from app.core.responses import openapi_error_responses


def create_app(app_settings: Settings | None = None) -> FastAPI:
    current_settings = app_settings or settings
    expose_api_docs = current_settings.app_env == "local"
    application = FastAPI(
        title="LoadX API",
        version="0.1.0",
        docs_url="/docs" if expose_api_docs else None,
        redoc_url="/redoc" if expose_api_docs else None,
        openapi_url="/openapi.json" if expose_api_docs else None,
    )
    register_exception_handlers(application)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api/v1")

    @application.get(
        "/health",
        tags=["health"],
        responses=openapi_error_responses(500),
    )
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "loadx-api"}

    return application


app = create_app()
