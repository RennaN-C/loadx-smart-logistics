from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]]


_ERROR_RESPONSE_DESCRIPTIONS = {
    401: "Autenticação ausente ou inválida.",
    403: "Acesso negado ou usuário inativo.",
    404: "Entidade relacionada não encontrada.",
    409: "Conflito de estado ou recurso duplicado.",
    422: "Dados de entrada inválidos.",
    500: "Erro interno inesperado.",
    503: "Serviço temporariamente indisponível.",
}


def openapi_error_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    return {
        status_code: {
            "model": ErrorResponse,
            "description": _ERROR_RESPONSE_DESCRIPTIONS[status_code],
        }
        for status_code in status_codes
    }


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={
            "code": code,
            "message": message,
            "details": details or [],
        },
    )
