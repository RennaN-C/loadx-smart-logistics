"""Short-lived, actor-bound proof of a real failed packing attempt; no persistence."""

import base64
import hashlib
import hmac
import re
import time
import uuid
from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.exceptions import ApiError
from app.modules.access_profiles.catalog import has_permission
from app.modules.users.models import User

TTL_SECONDS = 900
PURPOSE = b"loadx:assistant:optimization-failure:v1"
Reason = Literal[
    "COLLISION",
    "TRUCK_DIMENSIONS_EXCEEDED",
    "TRUCK_WEIGHT_EXCEEDED",
    "NON_STACKABLE_SUPPORT",
    "FRAGILE_SUPPORT_WEIGHT_EXCEEDED",
    "INSUFFICIENT_SUPPORT",
    "NO_VALID_POSITION",
]
REASONS = {
    "COLLISION",
    "TRUCK_DIMENSIONS_EXCEEDED",
    "TRUCK_WEIGHT_EXCEEDED",
    "NON_STACKABLE_SUPPORT",
    "FRAGILE_SUPPORT_WEIGHT_EXCEEDED",
    "INSUFFICIENT_SUPPORT",
    "NO_VALID_POSITION",
}


class AttemptDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    actor: uuid.UUID
    issued_at: int
    expires_at: int
    code: Literal["DISTRIBUTION_CAPACITY_INSUFFICIENT"]
    remaining_volumes: int = Field(ge=1, le=200)
    unavailable_trucks: int = Field(ge=0)
    reasons: dict[Reason, int]


def _signature(payload: str) -> str:
    key = hmac.digest(settings.secret_key.encode(), PURPOSE, "sha256")
    return hmac.new(key, payload.encode("ascii"), hashlib.sha256).hexdigest()


def issue_capacity_diagnostic(actor: uuid.UUID, details: list | None) -> str | None:
    detail = next(
        (
            item
            for item in details or []
            if isinstance(item, dict)
            and isinstance(item.get("remaining_volumes"), list)
        ),
        None,
    )
    if not detail or not 1 <= len(detail["remaining_volumes"]) <= 200:
        return None
    counts: Counter[str] = Counter()
    for volume in detail["remaining_volumes"]:
        if isinstance(volume, dict) and isinstance(volume.get("reasons"), list):
            # Each reason counts at most once per remaining physical volume.
            counts.update(
                {
                    reason
                    for reason in volume["reasons"]
                    if isinstance(reason, str) and reason in REASONS
                }
            )
    now = int(time.time())
    value = AttemptDiagnostic(
        actor=actor,
        issued_at=now,
        expires_at=now + TTL_SECONDS,
        code="DISTRIBUTION_CAPACITY_INSUFFICIENT",
        remaining_volumes=len(detail["remaining_volumes"]),
        unavailable_trucks=len(detail.get("ineligible_trucks", [])),
        reasons=dict(counts),
    )
    encoded = (
        base64.urlsafe_b64encode(value.model_dump_json().encode()).decode().rstrip("=")
    )
    return encoded + "." + _signature(encoded)


def read_capacity_diagnostic(token: str, user: User) -> AttemptDiagnostic:
    if user.role not in {"ADMIN", "LOGISTICS_MANAGER"} or not has_permission(
        user, "loadx.planning.create"
    ):
        raise ApiError(
            403, "AUTH_FORBIDDEN", "Seu perfil não pode consultar esta tentativa."
        )
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.[0-9a-f]{64}", token):
            raise ValueError
        encoded, signature = token.split(".")
        if not hmac.compare_digest(_signature(encoded), signature):
            raise ValueError
        diagnostic = AttemptDiagnostic.model_validate_json(
            base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        )
        now = int(time.time())
        if (
            diagnostic.actor != user.id
            or not diagnostic.issued_at <= now < diagnostic.expires_at
            or diagnostic.expires_at - diagnostic.issued_at != TTL_SECONDS
        ):
            raise ValueError
        return diagnostic
    except ValueError:
        raise ApiError(
            422,
            "ASSISTANT_DIAGNOSTIC_INVALID",
            "O diagnóstico expirou ou não pertence ao usuário autenticado. Consulte a operação sem repetir o cálculo automaticamente.",
        ) from None
