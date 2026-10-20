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
    signatures = request.headers.getlist("x-loadx-signature")
    if len(signatures) != 1 or len(signatures[0]) != 64:
        return _reject(request, 401, "EXTERNAL_AUTHENTICITY_INVALID")
    try:
        runtime.limiter.acquire_nowait()
    except anyio.WouldBlock:
        return _reject(request, 429, "INBOUND_BUSY")
    try:
        lengths = request.headers.getlist("content-length")
        if lengths and (
            len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit()
        ):
            return _reject(request, 400, "INBOUND_HEADERS_INVALID")
        if lengths and (len(lengths[0]) > 6 or int(lengths[0]) > MAX_BODY_BYTES):
            return _reject(request, 413, "INBOUND_BODY_TOO_LARGE")
        body = bytearray()
        try:
            with anyio.fail_after(BODY_TIMEOUT_SECONDS):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_BODY_BYTES:
                        return _reject(request, 413, "INBOUND_BODY_TOO_LARGE")
                    body.extend(chunk)
        except TimeoutError:
            return _reject(request, 408, "INBOUND_BODY_TIMEOUT")
        except ClientDisconnect:
            return _reject(request, 400, "INBOUND_REQUEST_INCOMPLETE")
        if lengths and int(lengths[0]) != len(body):
            return _reject(request, 400, "INBOUND_HEADERS_INVALID")
        # Authenticate before interpreting even content metadata or JSON. The
        # command service independently verifies the identical original bytes.
        try:
            runtime.commands.authenticator.authenticate(bytes(body), signatures[0])
            content_type = request.headers.getlist("content-type")
            if (
                len(content_type) != 1
                or content_type[0].lower().replace(" ", "")
                not in {
                    "application/json",
                    "application/json;charset=utf-8",
                }
                or request.headers.get("content-encoding", "identity").lower()
                != "identity"
            ):
                return _reject(request, 415, "INBOUND_CONTENT_TYPE_INVALID")
            return await run_in_threadpool(
                runtime.commands.process, bytes(body), signatures[0]
            )
        except ExternalCommandError as error:
            return _reject(request, ERROR_STATUS[error.code], error.code.value)
    finally:
        runtime.limiter.release()
