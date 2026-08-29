import uuid

import pytest
from pydantic import ValidationError

from app.modules.orders.schemas import (
    ORDER_PRIORITY_VALUES,
    OrderCreate,
    OrderUpdate,
)


def make_order_payload(priority: str) -> dict[str, object]:
    return {
        "customer_id": uuid.uuid4(),
        "priority": priority,
        "delivery_address": "Rua Exemplo, 100",
        "items": [
            {
                "product_id": uuid.uuid4(),
                "quantity": 1,
                "delivery_sequence": 1,
            }
        ],
    }


@pytest.mark.parametrize("priority", ORDER_PRIORITY_VALUES)
def test_order_create_accepts_and_normalizes_allowed_priority(priority: str) -> None:
    order = OrderCreate.model_validate(make_order_payload(priority.lower()))

    assert order.priority == priority


@pytest.mark.parametrize("priority", ORDER_PRIORITY_VALUES)
def test_order_update_accepts_and_normalizes_allowed_priority(priority: str) -> None:
    update = OrderUpdate.model_validate({"priority": priority.lower()})

    assert update.priority == priority


def test_order_create_rejects_unknown_priority() -> None:
    payload = make_order_payload("IMMEDIATE")

    with pytest.raises(ValidationError, match="priority must be one of") as exc_info:
        OrderCreate.model_validate(payload)

    assert exc_info.value.errors()[0]["loc"] == ("priority",)


def test_order_update_rejects_unknown_priority() -> None:
    with pytest.raises(ValidationError, match="priority must be one of") as exc_info:
        OrderUpdate.model_validate({"priority": "IMMEDIATE"})

    assert exc_info.value.errors()[0]["loc"] == ("priority",)
