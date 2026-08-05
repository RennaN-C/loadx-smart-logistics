from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    OrderItemInput,
    VolumeIdentity,
)


def test_optimizer_contracts_are_immutable() -> None:
    order_item = OrderItemInput(
        order_id=UUID("00000000-0000-0000-0000-000000000001"),
        order_item_id=UUID("00000000-0000-0000-0000-000000000002"),
        product_id=UUID("00000000-0000-0000-0000-000000000003"),
        product_name="Caixa A",
        quantity=1,
        delivery_sequence=2,
        width_cm=60,
        height_cm=50,
        length_cm=40,
        weight_kg=Decimal("12.500"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )
    volume = IndividualVolume(
        identity=VolumeIdentity(order_item_id=order_item.order_item_id, volume_index=1),
        order_id=order_item.order_id,
        product_id=order_item.product_id,
        product_name=order_item.product_name,
        delivery_sequence=order_item.delivery_sequence,
        original_width_cm=order_item.width_cm,
        original_height_cm=order_item.height_cm,
        original_length_cm=order_item.length_cm,
        volume_cm3=120_000,
        weight_kg=order_item.weight_kg,
        fragile=order_item.fragile,
        stackable=order_item.stackable,
        rotation_allowed=order_item.rotation_allowed,
    )

    with pytest.raises(FrozenInstanceError):
        order_item.quantity = 2
    with pytest.raises(FrozenInstanceError):
        volume.identity.volume_index = 2
    with pytest.raises(FrozenInstanceError):
        volume.volume_cm3 = 1
