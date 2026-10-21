import uuid
from datetime import UTC, datetime, timedelta
import pytest
from pydantic import ValidationError
from app.modules.deliveries.exception_schemas import DeliveryExceptionCreate


def test_oc94_requires_reason():
    with pytest.raises(ValidationError):
        DeliveryExceptionCreate(code="CUSTOMER_ABSENT", reason="curto", idempotency_key=uuid.uuid4())
    event = DeliveryExceptionCreate(code="CUSTOMER_ABSENT", reason="Cliente ausente no endereco informado", idempotency_key=uuid.uuid4())
    assert event.scheduled_for is None


def test_oc94_rescheduling_requires_aware_date():
    with pytest.raises(ValidationError):
        DeliveryExceptionCreate(code="RESCHEDULED", reason="Nova tentativa combinada com cliente", idempotency_key=uuid.uuid4())
    with pytest.raises(ValidationError):
        DeliveryExceptionCreate(code="RESCHEDULED", reason="Nova tentativa combinada com cliente", idempotency_key=uuid.uuid4(), scheduled_for=datetime.now())
    event = DeliveryExceptionCreate(code="RESCHEDULED", reason="Nova tentativa combinada com cliente", idempotency_key=uuid.uuid4(), scheduled_for=datetime.now(UTC) + timedelta(days=1))
    assert event.scheduled_for is not None


def test_oc94_rejects_unsafe_cancel_and_wrong_schedule():
    with pytest.raises(ValidationError):
        DeliveryExceptionCreate(code="CANCELLED", reason="Cancelamento nao aprovado pelo dominio", idempotency_key=uuid.uuid4())
    with pytest.raises(ValidationError):
        DeliveryExceptionCreate(code="DAMAGED", reason="Volume avariado durante entrega", idempotency_key=uuid.uuid4(), scheduled_for=datetime.now(UTC) + timedelta(days=1))
