import json
import uuid
from datetime import timedelta

import anyio
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.inbound_webhook import (
    InboundWebhookRuntime,
    build_inbound_webhook,
)
from app.main import create_app
from app.modules.messages import webhook_router
from tests.unit.test_external_command_validation import (
    NOW,
    command_body,
    sign,
    validation_service,
)

PATH = "/api/v1/webhooks/controlled-events"


def configured(**updates):
    return Settings(
        app_env="local",
        _env_file=None,
        **{
            "inbound_webhook_enabled": True,
            "inbound_webhook_signing_key": b"local-test-only-configuration-key-32-bytes",
            "inbound_webhook_bindings": json.dumps(
                {"fixture-subject": str(uuid.uuid4())}
            ),
            "inbound_webhook_capabilities": '["FINISH_DELIVERY"]',
            **updates,
        },
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"inbound_webhook_signing_key": None},
        {"inbound_webhook_signing_key": b"short"},
        {"inbound_webhook_signing_key": b"local-only"},
        {"secret_key": "a" * 40, "inbound_webhook_signing_key": b"a" * 40},
        {"inbound_webhook_bindings": "{}"},
        {"inbound_webhook_bindings": '{"invalid subject":"invalid-uuid"}'},
        {
            "inbound_webhook_bindings": json.dumps(
                {"invalid subject": str(uuid.uuid4())}
            )
        },
        {"inbound_webhook_capabilities": "[]"},
        {"inbound_webhook_capabilities": '["MEDIA"]'},
    ],
)
def test_invalid_enabled_configuration_fails_closed(updates):
    with pytest.raises(ValidationError) as error:
        configured(**updates)
    assert "input_value" not in str(error.value)


def test_default_disabled_and_exclusive_configuration():
    assert build_inbound_webhook(Settings(app_env="local", _env_file=None)) is None
    settings = configured()
    assert "local-test-only" not in repr(settings)
    runtime = build_inbound_webhook(settings)
    try:
        assert (
            runtime.commands.authenticator.integration.integration_id
            == "loadx-controlled-webhook"
        )
        assert runtime.commands.authenticator.integration.capabilities == {
            "FINISH_DELIVERY"
        }
    finally:
        runtime.engine.dispose()


@pytest.fixture
def transport():
    commands, factory, resolver = validation_service()
    app = create_app()
    app.state.inbound_webhook = InboundWebhookRuntime(commands)
    with TestClient(app) as client:
        yield client, factory, resolver
    factory.assert_not_called()
    resolver.resolve.assert_not_called()


@pytest.mark.parametrize("signature", [None, "0" * 64, "invalid", "F" * 64])
def test_invalid_signature_before_parsing_or_database(transport, signature):
    client, _, _ = transport
    response = client.post(
        PATH,
        content=b"not-json",
        headers={} if signature is None else {"X-LoadX-Signature": signature},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "EXTERNAL_AUTHENTICITY_INVALID"


def test_altered_bytes_and_duplicate_signature(transport):
    client, _, _ = transport
    body = command_body()
    assert (
        client.post(
            PATH, content=body + b" ", headers={"X-LoadX-Signature": sign(body)}
        ).status_code
        == 401
    )
    response = client.post(
        PATH,
        content=body,
        headers=[("X-LoadX-Signature", sign(body)), ("X-LoadX-Signature", sign(body))],
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b"[]",
        b'{"version":1,"version":1}',
        b"\xff",
        b"",
        b'{"nested":{"k":1,"k":2}}',
    ],
)
def test_signed_invalid_json_never_reaches_actor(transport, body):
    client, _, _ = transport
    response = client.post(
        PATH,
        content=body,
        headers={"Content-Type": "application/json", "X-LoadX-Signature": sign(body)},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "updates,code,status",
    [
        ({"version": True}, "EXTERNAL_PAYLOAD_INVALID", 422),
        ({"version": "1"}, "EXTERNAL_PAYLOAD_INVALID", 422),
        ({"version": 2}, "EXTERNAL_PAYLOAD_INVALID", 422),
        ({"role": "ADMIN"}, "EXTERNAL_PAYLOAD_INVALID", 422),
        (
            {
                "issued_at": (NOW + timedelta(seconds=31)).isoformat(),
                "expires_at": (NOW + timedelta(minutes=1)).isoformat(),
            },
            "EXTERNAL_COMMAND_NOT_YET_VALID",
            422,
        ),
        (
            {
                "issued_at": (NOW - timedelta(minutes=5)).isoformat(),
                "expires_at": NOW.isoformat(),
            },
            "EXTERNAL_COMMAND_EXPIRED",
            410,
        ),
        ({"message": "finalizar entrega"}, "EXTERNAL_PAYLOAD_INVALID", 422),
        (
            {"media_url": "https://untrusted.invalid/image"},
            "EXTERNAL_PAYLOAD_INVALID",
            422,
        ),
        ({"content_base64": "not-accepted"}, "EXTERNAL_PAYLOAD_INVALID", 422),
        ({"command": "ATTACH_MEDIA"}, "EXTERNAL_PAYLOAD_INVALID", 422),
    ],
)
def test_payload_time_and_disabled_media(transport, updates, code, status):
    client, _, _ = transport
    body = command_body(**updates)
    response = client.post(
        PATH,
        content=body,
        headers={"Content-Type": "application/json", "X-LoadX-Signature": sign(body)},
    )
    assert response.status_code == status
    assert response.json()["code"] == code


def test_size_and_content_metadata(transport):
    client, _, _ = transport
    body = b"x" * (16 * 1024 + 1)
    assert (
        client.post(
            PATH, content=body, headers={"X-LoadX-Signature": sign(body)}
        ).status_code
        == 413
    )
    body = command_body()
    for extra in (
        {"Content-Type": "text/plain"},
        {"Content-Type": "application/json", "Content-Encoding": "gzip"},
    ):
        assert (
            client.post(
                PATH, content=body, headers={"X-LoadX-Signature": sign(body), **extra}
            ).status_code
            == 415
        )


def test_inclusive_limit_and_ambiguous_content_metadata(transport):
    client, _, _ = transport
    body = b" " * (16 * 1024)
    assert (
        client.post(
            PATH,
            content=body,
            headers={
                "X-LoadX-Signature": sign(body),
                "Content-Type": "application/json",
            },
        ).status_code
        == 422
    )
    body = command_body()
    for metadata in (
        [("Content-Type", "application/json"), ("Content-Type", "text/plain")],
        [
            ("Content-Type", "application/json"),
            ("Content-Encoding", "identity"),
            ("Content-Encoding", "gzip"),
        ],
    ):
        response = client.post(
            PATH, content=body, headers=[("X-LoadX-Signature", sign(body)), *metadata]
        )
        assert response.status_code == 415


def test_disabled_and_browser_protections_unchanged():
    with TestClient(create_app()) as client:
        assert client.post(PATH).status_code == 503
        assert client.post("/api/v1/messages/interpret", json={}).status_code == 403
        assert client.post(PATH + "/", content=b"{}").status_code == 403
        assert client.patch(PATH, content=b"{}").status_code == 403
        response = client.options(
            PATH,
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-LoadX-Signature",
            },
        )
        assert response.status_code == 400


def test_stream_limits_timeout_and_overload(monkeypatch):
    async def exercise():
        app = create_app()
        commands, factory, _ = validation_service()
        runtime = InboundWebhookRuntime(commands)
        app.state.inbound_webhook = runtime

        async def send_request(chunks, headers=(), delay=0, disconnect=False):
            iterator = iter(chunks)

            async def receive():
                if disconnect:
                    return {"type": "http.disconnect"}
                if delay:
                    await anyio.sleep(delay)
                chunk = next(iterator, b"")
                return {"type": "http.request", "body": chunk, "more_body": bool(chunk)}

            from starlette.requests import Request

            request = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": PATH,
                    "headers": [(b"x-loadx-signature", b"0" * 64), *headers],
                    "app": app,
                },
                receive,
            )
            response = await webhook_router.receive_controlled_event(request)
            return response

        assert (await send_request([b"x" * 8000, b"x" * 9000])).status_code == 413
        assert (await send_request([], disconnect=True)).status_code == 400
        assert (
            await send_request([b"{}"], headers=[(b"content-length", b"3")])
        ).status_code == 400
        monkeypatch.setattr(webhook_router, "BODY_TIMEOUT_SECONDS", 0.01)
        assert (await send_request([b""], delay=0.1)).status_code == 408
        assert (
            await send_request([], headers=[(b"content-length", b"-1")])
        ).status_code == 400
        assert (
            await send_request([], headers=[(b"content-length", b"9" * 100)])
        ).status_code == 413
        borrowers = [object() for _ in range(4)]
        for borrower in borrowers:
            runtime.limiter.acquire_on_behalf_of_nowait(borrower)
        assert (await send_request([])).status_code == 429
        for borrower in borrowers:
            runtime.limiter.release_on_behalf_of(borrower)
        factory.assert_not_called()

    anyio.run(exercise)
