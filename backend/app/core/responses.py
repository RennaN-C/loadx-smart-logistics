from typing import Any

from fastapi.responses import JSONResponse


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details or [],
        },
    )
