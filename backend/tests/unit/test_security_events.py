import json
import logging

import pytest

from app.core.security_events import SecurityEvent, emit_security_event


def test_security_event_is_structured_and_marks_alert(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="loadx.security"):
        emit_security_event(
            SecurityEvent.LOGIN_FAILED,
            level=logging.WARNING,
            alert=True,
            known_account=True,
            privileged_account=True,
            delay_seconds=60,
        )

    payload = json.loads(caplog.records[0].getMessage())
    assert payload["event"] == "AUTH_LOGIN_FAILED"
    assert payload["alert"] is True
    assert payload["privileged_account"] is True
    assert payload["occurred_at"].endswith("+00:00")


@pytest.mark.parametrize(
    "field_name",
    ["email", "client_ip", "password_hash", "session_token", "secret_value"],
)
def test_security_event_rejects_sensitive_fields(field_name: str) -> None:
    with pytest.raises(ValueError, match="sensitive security event field"):
        emit_security_event(
            SecurityEvent.LOGIN_FAILED,
            **{field_name: "must-not-be-logged"},
        )
