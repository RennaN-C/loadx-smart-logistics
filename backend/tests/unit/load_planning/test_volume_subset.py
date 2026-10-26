import uuid
from dataclasses import replace
from decimal import Decimal

import pytest

from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import OrderItemInput, VolumeIdentity
from app.modules.load_planning.optimizer.engine import (
    InvalidEngineInputError,
    calculate_load_plan,
    calculate_volume_load_plan,
)
from app.modules.load_planning.optimizer.volumes import (
    InvalidVolumeInputError,
    expand_order_items,
)


def sources():
    item = OrderItemInput(
        order_id=uuid.uuid4(),
        order_item_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        quantity=4,
        delivery_sequence=1,
        width_cm=10,
        height_cm=10,
        length_cm=10,
        weight_kg=Decimal("1.000"),
        fragile=False,
        stackable=True,
        rotation_allowed=False,
    )
    truck = TruckCapacityInput(
        internal_width_cm=40,
        internal_height_cm=10,
        internal_length_cm=10,
        max_weight_kg=Decimal(100),
    )
    return item, truck


def test_full_subset_matches_legacy_engine_exactly():
    item, truck = sources()
    assert calculate_load_plan(truck, [item]) == calculate_volume_load_plan(
        truck, expand_order_items([item])
    )


def test_selected_indices_keep_identity_and_physical_rules():
    item, truck = sources()
    volumes = expand_order_items([item])
    result = calculate_volume_load_plan(truck, [volumes[1], volumes[3]])
    assert {v.volume.volume_index for v in result.placed_volumes} == {2, 4}
    assert (
        result.metrics.loaded_count == 2
        and result.metrics.total_weight_kg == Decimal("2.000")
    )


@pytest.mark.parametrize(
    "mutation", ["duplicate", "invalid_index", "invalid_volume", "invalid_weight"]
)
def test_subset_refuses_invalid_physical_units(mutation):
    item, truck = sources()
    volume = expand_order_items([item])[0]
    if mutation == "duplicate":
        selected = [volume, volume]
    else:
        updates = {
            "invalid_index": {"identity": VolumeIdentity(item.order_item_id, 0)},
            "invalid_volume": {"volume_cm3": 999},
            "invalid_weight": {"weight_kg": Decimal("NaN")},
        }
        selected = [replace(volume, **updates[mutation])]
    with pytest.raises((InvalidEngineInputError, InvalidVolumeInputError)):
        calculate_volume_load_plan(truck, selected)
