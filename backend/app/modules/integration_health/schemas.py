import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Component = Literal["api", "database", "whatsapp", "ai", "webhook", "notifications"]
IntegrationMode = Literal["INTERNAL", "MOCK", "REAL"]
HealthStatus = Literal[
    "AVAILABLE",
    "SIMULATED",
    "NOT_CONFIGURED",
    "NOT_IMPLEMENTED",
    "LIMITED",
    "UNAVAILABLE",
    "TIMEOUT",
]
ReasonCode = Literal[
    "LIVE",
    "READY",
    "READINESS_FAILED",
    "TIMEOUT",
    "MOCK_PROVIDER",
    "PROVIDER_NOT_IMPLEMENTED",
    "OC83_PENDING",
    "OC84_PENDING",
    "NOT_CONFIGURED",
    "APPROVAL_REQUIRED",
    "PROVIDER_FAILED",
    "INVALID_SIGNAL",
]


class ComponentHealth(BaseModel):
    component: Component
    mode: IntegrationMode
    status: HealthStatus
    configured: bool | None
    reason_code: ReasonCode
    model_config = ConfigDict(extra="forbid", frozen=True)


class IntegrationHealthReport(BaseModel):
    checked_at: datetime
    correlation_id: uuid.UUID
    overall_status: Literal["PARTIAL", "DEGRADED"]
    components: list[ComponentHealth]
    model_config = ConfigDict(extra="forbid", frozen=True)


class IntegrationSignal(BaseModel):
    """Port futuro: somente estado sanitizado; sem nomes de provider/credenciais."""

    mode: Literal["INTERNAL", "REAL"]
    configured: bool
    approved: bool
    status: Literal["AVAILABLE", "UNAVAILABLE", "TIMEOUT"]
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, revalidate_instances="always"
    )
