import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.responses import error_response

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def _validation_details(error: RequestValidationError) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for validation_error in error.errors():
        location = validation_error.get("loc", ())
        field_parts = [
            str(part) for part in location if part not in {"body", "path", "query"}
        ]
        details.append(
            {
                "field": ".".join(field_parts),
                "message": str(validation_error.get("msg", "Invalid value")),
                "type": str(validation_error.get("type", "value_error")),
            }
        )
    return details


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(
        _request: Request,
        error: ApiError,
    ) -> JSONResponse:
        return error_response(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            details=error.details,
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Os dados informados são inválidos.",
            details=_validation_details(error),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        logger.error(
            "Unhandled application error: method=%s path=%s exception_type=%s",
            request.method,
            request.url.path,
            type(error).__name__,
        )
        return error_response(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="Ocorreu um erro interno inesperado.",
        )
