import uuid
from unittest.mock import Mock

import pytest

from app.integrations.outbox import (
    DeliveryEnvelope,
    MockOutboxTransport,
    PermanentDeliveryError,
    TransientDeliveryError,
)
from app.integrations.whatsapp import MockWhatsAppProvider
from app.modules.notifications.outbox_service import (
    Claim,
    deliver,
    legacy_outcome,
    retry_delay,
)


@pytest.mark.parametrize(
    "attempt,bound", [(1, 30), (2, 60), (3, 120), (8, 3600), (100, 3600)]
)
@pytest.mark.parametrize(
    "jitter,scale", [(0, 0.5), (0.5, 0.75), (1, 1), (-1, 0.5), (2, 1)]
)
def test_backoff_is_bounded_and_has_nonzero_equal_jitter(attempt, bound, jitter, scale):
    assert (
        retry_delay(attempt, base_seconds=30, cap_seconds=3600, jitter=jitter)
        == bound * scale
    )


@pytest.mark.parametrize(
    "error,status,code",
    [
        (TransientDeliveryError(), "RETRYABLE", "TRANSIENT"),
        (PermanentDeliveryError(), "TERMINAL", "PERMANENT"),
        (TimeoutError(), "UNCERTAIN", "TIMEOUT_UNKNOWN"),
        (RuntimeError(), "UNCERTAIN", "UNKNOWN_RESULT"),
    ],
)
def test_error_classification_never_exposes_exception_message(error, status, code):
    transport = Mock()
    transport.send.side_effect = error
    assert deliver(
        transport, Claim(uuid.uuid4(), 1, DeliveryEnvelope("fixture", "fixture", "id"))
    ) == (status, code)


def test_mock_uses_existing_provider_without_retaining_private_history():
    provider = MockWhatsAppProvider()
    MockOutboxTransport(provider).send(
        DeliveryEnvelope("fixture-phone", "fixture-content", "key")
    )
    assert provider.sent_messages == []
    assert "fixture-phone" not in repr(
        DeliveryEnvelope("fixture-phone", "fixture-content", "key")
    )


@pytest.mark.parametrize(
    "status,target",
    [
        ("SIMULATED", "SUCCEEDED"),
        ("NO_RECIPIENT", "SUCCEEDED"),
        ("FAILED", "TERMINAL"),
        ("ATTEMPT_CLAIMED", "UNCERTAIN"),
    ],
)
def test_legacy_mapping_never_enqueues_a_previous_attempt(status, target):
    assert legacy_outcome(status)[0] == target
