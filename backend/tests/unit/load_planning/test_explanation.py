import uuid
from dataclasses import FrozenInstanceError, asdict
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.load_planning.explanation import (
    build_load_plan_explanation_context,
)
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder

PLAN_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")
SOURCE_PLAN_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
TRUCK_ID = uuid.UUID("00000000-0000-0000-0000-000000000200")
FIRST_ORDER_ID = uuid.UUID("00000000-0000-0000-0000-000000000301")
SECOND_ORDER_ID = uuid.UUID("00000000-0000-0000-0000-000000000302")


def make_item(
    *,
    suffix: int,
    order_id: uuid.UUID = FIRST_ORDER_ID,
    order_item_suffix: int | None = None,
    volume_index: int = 1,
    placed: bool = True,
    loading_sequence: int | None = 1,
    rejection_reason: str = "NO_VALID_POSITION",
) -> LoadPlanItem:
    order_item_value = order_item_suffix if order_item_suffix is not None else suffix
    if placed:
        placement: dict[str, object | None] = {
            "position_x_cm": suffix,
            "position_y_cm": 0,
            "position_z_cm": suffix * 2,
            "used_width_cm": 10,
            "used_height_cm": 20,
            "used_length_cm": 30,
            "rotation_code": "XYZ",
            "loading_sequence": loading_sequence,
            "rejection_reason": None,
        }
    else:
        placement = {
            "position_x_cm": None,
            "position_y_cm": None,
            "position_z_cm": None,
            "used_width_cm": None,
            "used_height_cm": None,
            "used_length_cm": None,
            "rotation_code": None,
            "loading_sequence": None,
            "rejection_reason": rejection_reason,
        }

    return LoadPlanItem(
        id=uuid.UUID(int=1_000 + suffix),
        load_plan_id=PLAN_ID,
        order_id=order_id,
        order_item_id=uuid.UUID(int=2_000 + order_item_value),
        product_id=uuid.UUID(int=3_000 + suffix),
        volume_index=volume_index,
        order_item_snapshot_quantity=2,
        order_item_snapshot_delivery_sequence=2,
        product_snapshot_code=f"PRODUCT-{suffix}",
        product_snapshot_name=f"Produto {suffix}",
        product_snapshot_width_cm=10,
        product_snapshot_height_cm=20,
        product_snapshot_length_cm=30,
        product_snapshot_weight_kg=Decimal("12.500"),
        product_snapshot_fragile=suffix % 2 == 0,
        product_snapshot_stackable=True,
        product_snapshot_rotation_allowed=True,
        placed=placed,
        **placement,
    )


def make_plan(
    *,
    items: list[LoadPlanItem],
    status: str = "CALCULATED",
    recalculated_from_id: uuid.UUID | None = SOURCE_PLAN_ID,
) -> LoadPlan:
    loaded_count = sum(item.placed for item in items)
    unloaded_count = len(items) - loaded_count
    used_volume_cm3 = loaded_count * 6_000
    order_ids = {item.order_id for item in items}

    return LoadPlan(
        id=PLAN_ID,
        truck_id=TRUCK_ID,
        recalculated_from_id=recalculated_from_id,
        status=status,
        truck_snapshot_plate="ABC1D23",
        truck_snapshot_model="Baú médio",
        truck_snapshot_internal_width_cm=100,
        truck_snapshot_internal_height_cm=100,
        truck_snapshot_internal_length_cm=100,
        truck_snapshot_max_weight_kg=Decimal("8000.00"),
        internal_volume_cm3=1_000_000,
        used_volume_cm3=used_volume_cm3,
        occupancy_percent=Decimal(used_volume_cm3) / Decimal(10000),
        total_weight_kg=Decimal("12.500") * loaded_count,
        loaded_count=loaded_count,
        unloaded_count=unloaded_count,
        algorithm_version="heuristic-v1",
        created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
        approved_at=(
            datetime(2026, 8, 20, 12, 5, tzinfo=UTC) if status == "APPROVED" else None
        ),
        orders=[
            LoadPlanOrder(load_plan_id=PLAN_ID, order_id=order_id)
            for order_id in sorted(order_ids, key=lambda value: -value.int)
        ],
        items=items,
    )


def item_state(item: LoadPlanItem) -> tuple[object, ...]:
    return (
        item.order_id,
        item.order_item_id,
        item.volume_index,
        item.placed,
        item.loading_sequence,
        item.rejection_reason,
        item.position_x_cm,
        item.position_y_cm,
        item.position_z_cm,
    )


def test_builds_complete_context_from_persisted_snapshots_and_metrics() -> None:
    loaded_second = make_item(
        suffix=2,
        order_id=SECOND_ORDER_ID,
        order_item_suffix=20,
        volume_index=2,
        loading_sequence=2,
    )
    loaded_first = make_item(
        suffix=1,
        order_id=FIRST_ORDER_ID,
        order_item_suffix=10,
        loading_sequence=1,
    )
    plan = make_plan(
        items=[loaded_second, loaded_first],
        status="APPROVED",
    )

    context = build_load_plan_explanation_context(plan)

    assert context.load_plan_id == PLAN_ID
    assert context.recalculated_from_id == SOURCE_PLAN_ID
    assert context.status == "APPROVED"
    assert context.order_ids == (FIRST_ORDER_ID, SECOND_ORDER_ID)
    assert context.truck.truck_id == TRUCK_ID
    assert context.truck.plate == "ABC1D23"
    assert context.truck.model == "Baú médio"
    assert (
        context.truck.internal_width_cm,
        context.truck.internal_height_cm,
        context.truck.internal_length_cm,
    ) == (100, 100, 100)
    assert context.truck.max_weight_kg == Decimal("8000.00")
    assert isinstance(context.truck.max_weight_kg, Decimal)
    assert context.internal_volume_cm3 == 1_000_000
    assert context.used_volume_cm3 == 12_000
    assert context.occupancy_percent == Decimal("1.2")
    assert context.total_weight_kg == Decimal("25.000")
    assert isinstance(context.occupancy_percent, Decimal)
    assert isinstance(context.total_weight_kg, Decimal)
    assert context.loaded_count == 2
    assert context.unloaded_count == 0
    assert context.algorithm_version == "heuristic-v1"
    assert [item.loading_sequence for item in context.placed_items] == [1, 2]
    assert [item.volume.order_item_id for item in context.placed_items] == [
        loaded_first.order_item_id,
        loaded_second.order_item_id,
    ]
    first_volume = context.placed_items[0].volume
    assert first_volume.order_id == FIRST_ORDER_ID
    assert first_volume.order_item_id == loaded_first.order_item_id
    assert first_volume.product_id == loaded_first.product_id
    assert first_volume.volume_index == 1
    assert first_volume.quantity == 2
    assert first_volume.delivery_sequence == 2
    assert first_volume.product_code == "PRODUCT-1"
    assert first_volume.product_name == "Produto 1"
    assert (
        first_volume.original_width_cm,
        first_volume.original_height_cm,
        first_volume.original_length_cm,
    ) == (10, 20, 30)
    assert first_volume.weight_kg == Decimal("12.500")
    assert first_volume.fragile is False
    assert first_volume.stackable is True
    assert first_volume.rotation_allowed is True
    assert (context.placed_items[0].x_cm, context.placed_items[0].z_cm) == (1, 2)
    assert context.placed_items[0].rotation_code == "XYZ"
    assert context.rejected_items == ()

    with pytest.raises(FrozenInstanceError):
        context.status = "CALCULATED"  # type: ignore[misc]


def test_builds_partial_context_with_stably_ordered_rejection_reasons() -> None:
    rejected_later_identity = make_item(
        suffix=4,
        order_id=SECOND_ORDER_ID,
        order_item_suffix=40,
        placed=False,
        rejection_reason="COLLISION",
    )
    loaded = make_item(
        suffix=1,
        order_id=FIRST_ORDER_ID,
        order_item_suffix=10,
        loading_sequence=1,
    )
    rejected_first_identity = make_item(
        suffix=3,
        order_id=FIRST_ORDER_ID,
        order_item_suffix=30,
        placed=False,
        rejection_reason="TRUCK_WEIGHT_EXCEEDED",
    )
    plan = make_plan(items=[rejected_later_identity, loaded, rejected_first_identity])

    context = build_load_plan_explanation_context(plan)

    assert context.status == "CALCULATED"
    assert context.loaded_count == 1
    assert context.unloaded_count == 2
    assert len(context.placed_items) == 1
    assert [item.volume.order_item_id for item in context.rejected_items] == [
        rejected_first_identity.order_item_id,
        rejected_later_identity.order_item_id,
    ]
    assert [item.rejection_reason for item in context.rejected_items] == [
        "TRUCK_WEIGHT_EXCEEDED",
        "COLLISION",
    ]


def test_builds_rejected_context_with_zero_metrics_and_no_placed_items() -> None:
    collision = make_item(
        suffix=2,
        order_item_suffix=20,
        placed=False,
        rejection_reason="COLLISION",
    )
    dimensions = make_item(
        suffix=1,
        order_item_suffix=10,
        placed=False,
        rejection_reason="TRUCK_DIMENSIONS_EXCEEDED",
    )
    plan = make_plan(items=[collision, dimensions], status="REJECTED")

    context = build_load_plan_explanation_context(plan)

    assert context.status == "REJECTED"
    assert context.placed_items == ()
    assert context.loaded_count == 0
    assert context.unloaded_count == 2
    assert context.used_volume_cm3 == 0
    assert context.occupancy_percent == Decimal(0)
    assert context.total_weight_kg == Decimal("0.000")
    assert [item.rejection_reason for item in context.rejected_items] == [
        "TRUCK_DIMENSIONS_EXCEEDED",
        "COLLISION",
    ]


def test_context_is_deterministic_and_does_not_mutate_the_source_plan() -> None:
    rejected = make_item(
        suffix=3,
        order_id=SECOND_ORDER_ID,
        order_item_suffix=30,
        placed=False,
        rejection_reason="INSUFFICIENT_SUPPORT",
    )
    loaded_second = make_item(
        suffix=2,
        order_id=SECOND_ORDER_ID,
        order_item_suffix=20,
        loading_sequence=2,
    )
    loaded_first = make_item(
        suffix=1,
        order_id=FIRST_ORDER_ID,
        order_item_suffix=10,
        loading_sequence=1,
    )
    plan = make_plan(items=[rejected, loaded_second, loaded_first])
    original_items = tuple(plan.items)
    original_orders = tuple(plan.orders)
    original_item_states = tuple(item_state(item) for item in plan.items)

    first = build_load_plan_explanation_context(plan)
    second = build_load_plan_explanation_context(plan)

    assert first == second
    assert asdict(first) == asdict(second)
    assert tuple(plan.items) == original_items
    assert tuple(plan.orders) == original_orders
    assert tuple(item_state(item) for item in plan.items) == original_item_states


def test_rejects_persisted_counts_that_disagree_with_item_partitions() -> None:
    plan = make_plan(items=[make_item(suffix=1)])
    plan.loaded_count = 0

    with pytest.raises(ValueError, match="counts must match"):
        build_load_plan_explanation_context(plan)


def test_rejects_non_contiguous_loading_sequence_without_reordering_source() -> None:
    first = make_item(suffix=1, loading_sequence=1)
    third = make_item(suffix=2, loading_sequence=3)
    plan = make_plan(items=[third, first])
    original_items = tuple(plan.items)

    with pytest.raises(ValueError, match="loading_sequence values must be contiguous"):
        build_load_plan_explanation_context(plan)

    assert tuple(plan.items) == original_items


def test_rejects_duplicate_volume_identity() -> None:
    first = make_item(suffix=1, order_item_suffix=10, loading_sequence=1)
    duplicate = make_item(suffix=2, order_item_suffix=10, loading_sequence=2)
    plan = make_plan(items=[first, duplicate])

    with pytest.raises(ValueError, match="volume identities must be unique"):
        build_load_plan_explanation_context(plan)
