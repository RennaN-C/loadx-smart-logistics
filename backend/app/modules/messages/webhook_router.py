"""Bounded HTTP transport delegating all mutable commands to OC79."""

import logging
import uuid

import anyio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from app.core.responses import error_response, openapi_error_responses
from app.core.security_events import SecurityEvent, emit_security_event
from app.integrations.inbound_webhook import BODY_TIMEOUT_SECONDS
from app.modules.external_commands.errors import (
    ExternalCommandError,
    ExternalCommandErrorCode,
)
from app.modules.external_commands.schemas import (
    ExternalCommandEnvelope,
    ExternalCommandReceipt,
)
from app.modules.external_commands.service import MAX_BODY_BYTES

router = APIRouter(prefix="/webhooks", tags=["controlled-inbound"])
ERROR_STATUS = {
    ExternalCommandErrorCode.AUTHENTICITY_INVALID: 401,
    ExternalCommandErrorCode.PAYLOAD_INVALID: 422,
    ExternalCommandErrorCode.EXPIRED: 410,
    ExternalCommandErrorCode.NOT_YET_VALID: 422,
    ExternalCommandErrorCode.FORBIDDEN: 403,
    ExternalCommandErrorCode.IDENTITY_CONFLICT: 409,
    ExternalCommandErrorCode.DOMAIN_REJECTED: 409,
    ExternalCommandErrorCode.PROCESSING_FAILED: 500,
}


class InboundTransportError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code


def _signature(request: Request) -> str:
    signatures = request.headers.getlist("x-loadx-signature")
    if len(signatures) != 1 or len(signatures[0]) != 64:
        raise InboundTransportError(401, "EXTERNAL_AUTHENTICITY_INVALID")
    return signatures[0]


def _declared_length(request: Request) -> int | None:
    lengths = request.headers.getlist("content-length")
    if not lengths:
        return None
    if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
        raise InboundTransportError(400, "INBOUND_HEADERS_INVALID")
    if len(lengths[0]) > 6 or int(lengths[0]) > MAX_BODY_BYTES:
        raise InboundTransportError(413, "INBOUND_BODY_TOO_LARGE")
    return int(lengths[0])


async def _read_body(request: Request) -> bytes:
    declared = _declared_length(request)
    body = bytearray()
    try:
        with anyio.fail_after(BODY_TIMEOUT_SECONDS):
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    raise InboundTransportError(413, "INBOUND_BODY_TOO_LARGE")
                body.extend(chunk)
    except TimeoutError:
        raise InboundTransportError(408, "INBOUND_BODY_TIMEOUT") from None
    except ClientDisconnect:
        raise InboundTransportError(400, "INBOUND_REQUEST_INCOMPLETE") from None
    if declared is not None and declared != len(body):
        raise InboundTransportError(400, "INBOUND_HEADERS_INVALID")
    return bytes(body)


def _validate_content_metadata(request: Request) -> None:
    content_types = request.headers.getlist("content-type")
    encodings = request.headers.getlist("content-encoding")
    if (
        len(content_types) != 1
        or content_types[0].lower().replace(" ", "")
        not in {"application/json", "application/json;charset=utf-8"}
        or len(encodings) > 1
        or (encodings and encodings[0].lower() != "identity")
    ):
        raise InboundTransportError(415, "INBOUND_CONTENT_TYPE_INVALID")


def _envelope_schema() -> dict:
    schema = ExternalCommandEnvelope.model_json_schema()
    schema["properties"]["command"] = schema.pop("$defs")["CommandName"]
    return schema


def _reject(request: Request, status: int, code: str) -> JSONResponse:
    emit_security_event(
        SecurityEvent.INBOUND_WEBHOOK_REJECTED,
        level=logging.WARNING,
        alert=True,
        correlation_id=getattr(request.state, "request_id", str(uuid.uuid4())),
        code=code,
    )
    return error_response(
        status,
        code,
        "Evento inbound rejeitado.",
        headers={"Retry-After": "1"} if status in {429, 503} else None,
    )


@router.post(
    "/controlled-events",
    response_model=ExternalCommandReceipt,
    responses=openapi_error_responses(
        400, 401, 403, 408, 409, 410, 413, 415, 422, 429, 500, 503
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _envelope_schema()}},
        },
        "parameters": [
            {
                "name": "X-LoadX-Signature",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            }
        ],
    },
    description="Emissor controlado OC83. HMAC-SHA-256 dos bytes originais; não é webhook Meta. Mídia não é aceita.",
)
async def receive_controlled_event(
    request: Request,
) -> ExternalCommandReceipt | JSONResponse:
    runtime = request.app.state.inbound_webhook
    if runtime is None:
        return _reject(request, 503, "INBOUND_NOT_CONFIGURED")
    try:
        signature = _signature(request)
        runtime.limiter.acquire_nowait()
    except InboundTransportError as error:
        return _reject(request, error.status, error.code)
    except anyio.WouldBlock:
        return _reject(request, 429, "INBOUND_BUSY")
    try:
        body = await _read_body(request)
        # Authenticate before interpreting even content metadata or JSON. The
        # command service independently verifies the identical original bytes.
        runtime.commands.authenticator.authenticate(body, signature)
        _validate_content_metadata(request)
        return await run_in_threadpool(runtime.commands.process, body, signature)
    except InboundTransportError as error:
        return _reject(request, error.status, error.code)
    except ExternalCommandError as error:
        return _reject(request, ERROR_STATUS[error.code], error.code.value)
    finally:
        runtime.limiter.release()
