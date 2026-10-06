import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from pydantic import SecretBytes

from app.integrations.external_commands import (
    HmacExternalAuthenticator,
    TrustedIntegration,
)
from app.modules.external_commands.errors import ExternalCommandError
from app.modules.external_commands.schemas import CommandName
from app.modules.external_commands.service import MAX_BODY_BYTES, ExternalCommandService

NOW = datetime(2026, 10, 6, 12, tzinfo=UTC)
KEY = bytes(range(32))


def command_body(**updates) -> bytes:
    data = {
        "version": 1,
        "event_id": "fixture-event",
        "subject": "fixture-subject",
        "command": "FINISH_DELIVERY",
        "target_id": str(uuid.uuid4()),
        "issued_at": NOW.isoformat(),
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
    }
    data.update(updates)
    return json.dumps(data, separators=(",", ":")).encode()


def sign(body: bytes) -> str:
    return hmac.new(KEY, body, hashlib.sha256).hexdigest()


def validation_service(**kwargs):
    factory = Mock(side_effect=AssertionError("database must not be used"))
    resolver = Mock(side_effect=AssertionError("actor must not be resolved"))
    trusted = TrustedIntegration("fixture", frozenset(CommandName))
    service = ExternalCommandService(
        factory,
        HmacExternalAuthenticator(trusted, SecretBytes(KEY)),
        resolver,
        clock=lambda: NOW,
        **kwargs,
    )
    return service, factory, resolver


@pytest.mark.parametrize(
    "updates",
    (
        {"role": "ADMIN"},
        {"user_id": str(uuid.uuid4())},
        {"permissions": ["all"]},
        {"integration_id": "spoofed"},
        {"command": "NEW_COMMAND"},
        {"version": True},
        {"version": "1"},
        {"version": 2},
        {"event_id": ""},
        {"event_id": "a" * 129},
        {"event_id": "with spaces"},
        {"subject": ""},
        {"subject": "a" * 129},
        {"subject": 12},
        {"target_id": "invalid"},
        {"issued_at": "2026-10-06T12:00:00"},
        {"expires_at": (NOW + timedelta(minutes=6)).isoformat()},
        {"expires_at": NOW.isoformat()},
        {"expires_at": (NOW - timedelta(seconds=1)).isoformat()},
    ),
)
def test_invalid_payload_never_reaches_actor_or_domain(updates):
    service, factory, resolver = validation_service()
    body = command_body(**updates)
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_PAYLOAD_INVALID$"):
        service.process(body, sign(body))
    factory.assert_not_called()
    resolver.resolve.assert_not_called()


@pytest.mark.parametrize(
    "body",
    (
        b"not-json",
        b"[]",
        b'{"version":1,"version":1}',
        b'{"version":1,"payload":{"a":1,"a":2}}',
        b"\xff",
        b"",
        b"x" * (MAX_BODY_BYTES + 1),
    ),
)
def test_malformed_ambiguous_or_oversized_body_is_rejected(body):
    service, factory, resolver = validation_service()
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_PAYLOAD_INVALID$"):
        service.process(body, sign(body))
    factory.assert_not_called()
    resolver.resolve.assert_not_called()


@pytest.mark.parametrize(
    "updates,code",
    (
        (
            {
                "issued_at": (NOW - timedelta(minutes=5)).isoformat(),
                "expires_at": NOW.isoformat(),
            },
            "EXTERNAL_COMMAND_EXPIRED",
        ),
        (
            {
                "issued_at": (NOW + timedelta(seconds=31)).isoformat(),
                "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
            },
            "EXTERNAL_COMMAND_NOT_YET_VALID",
        ),
    ),
)
def test_expired_or_future_event_is_denied_before_identity(updates, code):
    service, factory, resolver = validation_service()
    body = command_body(**updates)
    with pytest.raises(ExternalCommandError, match=f"^{code}$"):
        service.process(body, sign(body))
    factory.assert_not_called()
    resolver.resolve.assert_not_called()


def test_authenticity_is_checked_before_payload_and_logs_are_allowlisted(caplog):
    service, factory, resolver = validation_service()
    body = b"sensitive-token-password-payload"
    signature = "sensitive-signature"
    with (
        caplog.at_level(logging.WARNING, logger="loadx.security"),
        pytest.raises(
            ExternalCommandError, match="^EXTERNAL_AUTHENTICITY_INVALID$"
        ) as caught,
    ):
        service.process(body, signature)
    factory.assert_not_called()
    resolver.resolve.assert_not_called()
    record = json.loads(caplog.records[-1].getMessage())
    assert set(record) == {"alert", "event", "occurred_at", "correlation_id", "code"}
    assert uuid.UUID(record["correlation_id"])
    assert body.decode() not in caplog.text + str(caught.value)
    assert signature not in caplog.text + str(caught.value)
    assert KEY.hex() not in caplog.text + str(caught.value)


def test_missing_integration_capability_never_resolves_an_actor():
    service, factory, resolver = validation_service()
    service.authenticator = HmacExternalAuthenticator(
        TrustedIntegration("fixture", frozenset()), SecretBytes(KEY)
    )
    body = command_body()
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_COMMAND_FORBIDDEN$"):
        service.process(body, sign(body))
    factory.assert_not_called()
    resolver.resolve.assert_not_called()


def test_adapter_failure_is_sanitized_without_database_or_payload_log(caplog):
    service, factory, _resolver = validation_service()
    service.authenticator = Mock()
    service.authenticator.authenticate.side_effect = RuntimeError("private-token")
    body = command_body()
    with pytest.raises(
        ExternalCommandError, match="^EXTERNAL_PROCESSING_FAILED$"
    ) as caught:
        service.process(body, sign(body))
    factory.assert_not_called()
    assert caught.value.__suppress_context__
    assert "private-token" not in caplog.text + str(caught.value)
