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
    RECOVERY_REQUESTED = "AUTH_RECOVERY_REQUESTED"
    RECOVERY_CONSUMED = "AUTH_RECOVERY_CONSUMED"
    RECOVERY_REJECTED = "AUTH_RECOVERY_REJECTED"
    RECOVERY_DELIVERY_FAILED = "AUTH_RECOVERY_DELIVERY_FAILED"
    TRUSTED_DEVICE_CREATED = "AUTH_TRUSTED_DEVICE_CREATED"
    TRUSTED_DEVICE_USED = "AUTH_TRUSTED_DEVICE_USED"
    TRUSTED_DEVICES_REVOKED = "AUTH_TRUSTED_DEVICES_REVOKED"
    MFA_CONFIGURED = "AUTH_MFA_CONFIGURED"
    MFA_VALIDATED = "AUTH_MFA_VALIDATED"
    MFA_REJECTED = "AUTH_MFA_REJECTED"
    MFA_RECOVERY_USED = "AUTH_MFA_RECOVERY_USED"
    MFA_CODES_REGENERATED = "AUTH_MFA_CODES_REGENERATED"
    MFA_DISABLED = "AUTH_MFA_DISABLED"
    OWN_PROFILE_UPDATED = "AUTH_OWN_PROFILE_UPDATED"
    OWN_PASSWORD_REJECTED = "AUTH_OWN_PASSWORD_REJECTED"
    OWN_PASSWORD_CHANGED = "AUTH_OWN_PASSWORD_CHANGED"
    LOGIN_SUCCEEDED = "AUTH_LOGIN_SUCCEEDED"
    LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    SESSION_CREATED = "AUTH_SESSION_CREATED"
    SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    SESSION_REVOKED = "AUTH_SESSION_REVOKED"
    USER_SESSIONS_REVOKED = "AUTH_USER_SESSIONS_REVOKED"
    USER_SECURITY_STATE_CHANGED = "AUTH_USER_SECURITY_STATE_CHANGED"
    EXTERNAL_COMMAND_COMPLETED = "EXTERNAL_COMMAND_COMPLETED"
    EXTERNAL_COMMAND_REJECTED = "EXTERNAL_COMMAND_REJECTED"
    DELIVERY_EVIDENCE_REGISTERED = "DELIVERY_EVIDENCE_REGISTERED"
    DELIVERY_EVIDENCE_REVOKED = "DELIVERY_EVIDENCE_REVOKED"
    DELIVERY_EVIDENCE_CLEANUP_FAILED = "DELIVERY_EVIDENCE_CLEANUP_FAILED"


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
