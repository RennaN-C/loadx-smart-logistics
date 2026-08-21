import json
import logging
from datetime import UTC, datetime
from enum import StrEnum

logger = logging.getLogger("loadx.security")
_FORBIDDEN_FIELD_PARTS = frozenset(
    {"document", "email", "ip", "password", "secret", "token"}
)
_SAFE_SENSITIVE_METADATA_FIELDS = frozenset({"password_changed"})


class SecurityEvent(StrEnum):
    LOGIN_SUCCEEDED = "AUTH_LOGIN_SUCCEEDED"
    LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    SESSION_CREATED = "AUTH_SESSION_CREATED"
    SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    SESSION_REVOKED = "AUTH_SESSION_REVOKED"
    USER_SESSIONS_REVOKED = "AUTH_USER_SESSIONS_REVOKED"
    USER_SECURITY_STATE_CHANGED = "AUTH_USER_SECURITY_STATE_CHANGED"


def emit_security_event(
    event: SecurityEvent,
    *,
    level: int = logging.INFO,
    alert: bool = False,
    **details: str | int | bool,
) -> None:
    for field_name, value in details.items():
        normalized_name = field_name.casefold()
        if normalized_name not in _SAFE_SENSITIVE_METADATA_FIELDS and any(
            part in normalized_name for part in _FORBIDDEN_FIELD_PARTS
        ):
            raise ValueError(f"sensitive security event field: {field_name}")
        if not isinstance(value, str | int | bool):
            raise TypeError(f"unsupported security event value: {field_name}")

    payload: dict[str, str | int | bool] = {
        "alert": alert,
        "event": event.value,
        "occurred_at": datetime.now(UTC).isoformat(),
        **details,
    }
    logger.log(
        level,
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
    )
