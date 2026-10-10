import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Protocol

from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.core.health import liveness_status
from app.core.observability import OperationalEvent, emit_operational_event
from app.database.readiness import (
    DatabaseReadinessChecker,
    ReadinessCheckError,
    ReadinessFailureReason,
)
from app.modules.integration_health.schemas import (
    Component,
    ComponentHealth,
    IntegrationHealthReport,
    IntegrationSignal,
)


class IntegrationHealthSource(Protocol):
    async def read_signal(self, *, timeout_seconds: float) -> IntegrationSignal:
        """Estado já observado pelo adapter aprovado; não envia mensagem ou prompt."""


class IntegrationHealthService:
    def __init__(
        self,
        checker: DatabaseReadinessChecker,
        *,
        ai_provider: str = "mock",
        sources: dict[str, IntegrationHealthSource] | None = None,
        signal_timeout_seconds: float = 1.0,
    ) -> None:
        if signal_timeout_seconds <= 0:
            raise ValueError("signal timeout must be positive")
        self.checker = checker
        self.ai_provider = ai_provider
        self.sources = sources or {}
        self.signal_timeout_seconds = signal_timeout_seconds

    async def report(self, correlation_id: uuid.UUID) -> IntegrationHealthReport:
        database, ai, webhook, notifications = await asyncio.gather(
            self._database(),
            self._integration("ai"),
            self._integration("webhook"),
            self._integration("notifications"),
        )
        components = [
            ComponentHealth(
                component="api",
                mode="INTERNAL",
                status="AVAILABLE"
                if liveness_status()["status"] == "ok"
                else "UNAVAILABLE",
                configured=True,
                reason_code="LIVE",
            ),
            database,
            ComponentHealth(
                component="whatsapp",
                mode="MOCK",
                status="SIMULATED",
                configured=True,
                reason_code="MOCK_PROVIDER",
            ),
            ai,
            webhook,
            notifications,
        ]

        for item in components:
            if item.status in {"UNAVAILABLE", "TIMEOUT"}:
                emit_operational_event(
                    OperationalEvent.INTEGRATION_HEALTH_FAILED,
                    level=logging.WARNING,
                    alert=True,
                    reason=f"{item.component.upper()}_{item.reason_code}",
                )
        return IntegrationHealthReport(
            checked_at=datetime.now(UTC),
            correlation_id=correlation_id,
            overall_status="DEGRADED"
            if any(item.status in {"UNAVAILABLE", "TIMEOUT"} for item in components)
            else "PARTIAL",
            components=components,
        )

    async def _database(self) -> ComponentHealth:
        status, reason = "AVAILABLE", "READY"
        try:
            await asyncio.wait_for(
                run_in_threadpool(self.checker.check),
                timeout=self.checker.timeout_seconds + 1.0,
            )
        except ReadinessCheckError as error:
            status = (
                "TIMEOUT"
                if error.reason == ReadinessFailureReason.TIMEOUT
                else "UNAVAILABLE"
            )
            reason = "TIMEOUT" if status == "TIMEOUT" else "READINESS_FAILED"
        except TimeoutError:
            status, reason = "TIMEOUT", "TIMEOUT"
        except Exception:  # noqa: BLE001 - isolate and sanitize diagnostic failures
            status, reason = "UNAVAILABLE", "READINESS_FAILED"
        return ComponentHealth(
            component="database",
            mode="INTERNAL",
            status=status,
            configured=True,
            reason_code=reason,
        )

    def _default(self, component: Component) -> ComponentHealth:
        if component == "ai":
            mock = self.ai_provider == "mock"
            return ComponentHealth(
                component=component,
                mode="MOCK" if mock else "REAL",
                status="SIMULATED" if mock else "NOT_CONFIGURED",
                configured=mock,
                reason_code="MOCK_PROVIDER" if mock else "PROVIDER_NOT_IMPLEMENTED",
            )
        if component == "webhook":
            return ComponentHealth(
                component=component,
                mode="INTERNAL",
                status="NOT_IMPLEMENTED",
                configured=False,
                reason_code="OC83_PENDING",
            )
        return ComponentHealth(
            component=component,
            mode="INTERNAL",
            status="LIMITED",
            configured=True,
            reason_code="OC84_PENDING",
        )

    async def _integration(self, component: Component) -> ComponentHealth:
        source = self.sources.get(component)
        if source is None:
            return self._default(component)
        mode = "REAL" if component == "ai" else "INTERNAL"
        try:
            signal = await asyncio.wait_for(
                source.read_signal(timeout_seconds=self.signal_timeout_seconds),
                timeout=self.signal_timeout_seconds,
            )
            signal = IntegrationSignal.model_validate(signal)
            if signal.mode != mode:
                return self._failure(component, mode, "INVALID_SIGNAL")
            if not signal.approved:
                return ComponentHealth(
                    component=component,
                    mode=mode,
                    status="NOT_CONFIGURED",
                    configured=signal.configured,
                    reason_code="APPROVAL_REQUIRED",
                )
            if not signal.configured:
                return ComponentHealth(
                    component=component,
                    mode=mode,
                    status="NOT_CONFIGURED",
                    configured=False,
                    reason_code="NOT_CONFIGURED",
                )
            reason = {
                "AVAILABLE": "READY",
                "UNAVAILABLE": "PROVIDER_FAILED",
                "TIMEOUT": "TIMEOUT",
            }[signal.status]
            return ComponentHealth(
                component=component,
                mode=mode,
                status=signal.status,
                configured=True,
                reason_code=reason,
            )
        except ValidationError:
            return self._failure(component, mode, "INVALID_SIGNAL")
        except TimeoutError:
            return self._failure(component, mode, "TIMEOUT")
        except Exception:  # noqa: BLE001 - isolate and sanitize diagnostic failures
            return self._failure(component, mode, "PROVIDER_FAILED")

    @staticmethod
    def _failure(component: Component, mode: str, reason: str) -> ComponentHealth:
        return ComponentHealth(
            component=component,
            mode=mode,
            status="TIMEOUT" if reason == "TIMEOUT" else "UNAVAILABLE",
            configured=None,
            reason_code=reason,
        )
