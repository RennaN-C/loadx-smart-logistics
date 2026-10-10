import asyncio
import uuid
from dataclasses import dataclass

import pytest

from app.database.readiness import ReadinessCheckError, ReadinessFailureReason
from app.modules.integration_health.schemas import IntegrationSignal
from app.modules.integration_health.service import IntegrationHealthService


@dataclass
class Checker:
    error: Exception | None = None
    timeout_seconds: float = 0.1

    def check(self):
        if self.error:
            raise self.error


class Source:
    def __init__(self, signal=None, error=None, delay=0):
        self.signal, self.error, self.delay = signal, error, delay

    async def read_signal(self, *, timeout_seconds):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.signal


def report(checker=None, **kwargs):
    return asyncio.run(
        IntegrationHealthService(checker or Checker(), **kwargs).report(uuid.uuid4())
    )


def component(result, name):
    return next(item for item in result.components if item.component == name)


def test_current_components_are_honest_without_external_io():
    result = report()
    assert result.overall_status == "PARTIAL"
    assert component(result, "api").status == "AVAILABLE"
    assert component(result, "database").status == "AVAILABLE"
    assert component(result, "whatsapp").status == "SIMULATED"
    assert component(result, "ai").status == "SIMULATED"
    assert component(result, "webhook").status == "NOT_IMPLEMENTED"
    assert component(result, "notifications").status == "LIMITED"


@pytest.mark.parametrize("name", ["", "external", "secret-provider-url-token"])
def test_unknown_ai_configuration_never_implies_real_availability(name):
    result = report(ai_provider=name)
    ai = component(result, "ai")
    assert ai.status == "NOT_CONFIGURED"
    assert ai.reason_code == "PROVIDER_NOT_IMPLEMENTED"
    assert name not in result.model_dump_json() if name else True


@pytest.mark.parametrize("reason", list(ReadinessFailureReason))
def test_readiness_failure_is_sanitized_and_partial(reason):
    result = report(Checker(ReadinessCheckError(reason)))
    assert result.overall_status == "DEGRADED"
    assert component(result, "database").status == (
        "TIMEOUT" if reason == ReadinessFailureReason.TIMEOUT else "UNAVAILABLE"
    )
    assert component(result, "whatsapp").status == "SIMULATED"
    assert component(result, "api").status == "AVAILABLE"


@pytest.mark.parametrize(
    "error",
    [RuntimeError("token=password trace private://host"), TimeoutError("secret")],
)
def test_unexpected_database_errors_do_not_escape(error):
    result = report(Checker(error))
    assert component(result, "database").status in {"TIMEOUT", "UNAVAILABLE"}
    assert "secret" not in result.model_dump_json()
    assert "password" not in result.model_dump_json()


@pytest.mark.parametrize(
    "name,mode",
    [("ai", "REAL"), ("webhook", "INTERNAL"), ("notifications", "INTERNAL")],
)
@pytest.mark.parametrize("status", ["AVAILABLE", "UNAVAILABLE", "TIMEOUT"])
def test_registered_approved_sources_expose_only_safe_status(name, mode, status):
    source = Source(
        IntegrationSignal(mode=mode, configured=True, approved=True, status=status)
    )
    result = report(sources={name: source})
    item = component(result, name)
    assert item.status == status
    assert item.configured
    assert item.mode == mode


@pytest.mark.parametrize(
    "configured,approved,reason",
    [
        (False, True, "NOT_CONFIGURED"),
        (True, False, "APPROVAL_REQUIRED"),
        (False, False, "APPROVAL_REQUIRED"),
    ],
)
def test_ai_requires_configuration_and_approval(configured, approved, reason):
    signal = IntegrationSignal(
        mode="REAL", configured=configured, approved=approved, status="AVAILABLE"
    )
    item = component(report(sources={"ai": Source(signal)}), "ai")
    assert item.status == "NOT_CONFIGURED"
    assert item.reason_code == reason


@pytest.mark.parametrize(
    "source",
    [
        Source(error=RuntimeError("sensitive-token")),
        Source(
            {
                "mode": "REAL",
                "configured": True,
                "approved": True,
                "status": "AVAILABLE",
                "token": "sensitive-token",
            }
        ),
        Source(
            IntegrationSignal(
                mode="INTERNAL", configured=True, approved=True, status="AVAILABLE"
            )
        ),
    ],
)
def test_failure_and_invalid_signal_are_sanitized(source):
    result = report(sources={"ai": source})
    assert component(result, "ai").status == "UNAVAILABLE"
    assert "sensitive-token" not in result.model_dump_json()
    assert component(result, "ai").configured is None


def test_timeout_cancels_async_signal_and_preserves_other_components():
    result = report(sources={"ai": Source(delay=10)}, signal_timeout_seconds=0.01)
    assert component(result, "ai").status == "TIMEOUT"
    assert component(result, "whatsapp").status == "SIMULATED"


def test_whatsapp_cannot_be_activated_by_registered_source():
    source = Source(
        IntegrationSignal(
            mode="REAL", configured=True, approved=True, status="AVAILABLE"
        )
    )
    assert (
        component(report(sources={"whatsapp": source}), "whatsapp").status
        == "SIMULATED"
    )


def test_failures_emit_correlatable_safe_events(caplog):
    with caplog.at_level("WARNING", logger="loadx.operations"):
        report(sources={"ai": Source(error=RuntimeError("password-secreto"))})
    assert "INTEGRATION_HEALTH_FAILED" in caplog.text
    assert "AI_PROVIDER_FAILED" in caplog.text
    assert "password-secreto" not in caplog.text


def test_timeout_must_be_positive():
    with pytest.raises(ValueError):
        IntegrationHealthService(Checker(), signal_timeout_seconds=0)
