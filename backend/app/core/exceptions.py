from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


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
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Os dados informados são inválidos.",
                "details": _validation_details(error),
            },
        )
