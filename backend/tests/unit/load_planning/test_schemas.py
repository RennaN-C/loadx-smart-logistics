import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.load_planning.schemas import (
    LoadPlanCreate,
    LoadPlanItemRead,
    LoadPlanRead,
    PlacedLoadPlanItemRead,
    UnloadedLoadPlanItemRead,
    map_load_plan_item,
    map_load_plan_read,
    map_load_plan_visualization,
)

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
    quantity: int = 2,
    placed: bool = True,
    loading_sequence: int | None = 1,
    rejection_reason: str | None = None,
) -> LoadPlanItem:
    order_item_value = order_item_suffix if order_item_suffix is not None else suffix
    placement_values: dict[str, object | None]
    if placed:
        placement_values = {
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
        placement_values = {
            "position_x_cm": None,
            "position_y_cm": None,
            "position_z_cm": None,
            "used_width_cm": None,
            "used_height_cm": None,
            "used_length_cm": None,
            "rotation_code": None,
            "loading_sequence": None,
            "rejection_reason": rejection_reason or "NO_VALID_POSITION",
        }

    return LoadPlanItem(
        id=uuid.UUID(int=1_000 + suffix),
        load_plan_id=PLAN_ID,
        order_id=order_id,
        order_item_id=uuid.UUID(int=2_000 + order_item_value),
        product_id=uuid.UUID(int=3_000 + suffix),
        volume_index=volume_index,
        order_item_snapshot_quantity=quantity,
        order_item_snapshot_delivery_sequence=2,
        product_snapshot_code=f"PRODUCT-{suffix}",
        product_snapshot_name=f"Produto {suffix}",
        product_snapshot_width_cm=10,
        product_snapshot_height_cm=20,
        product_snapshot_length_cm=30,
        product_snapshot_weight_kg=Decimal("12.500"),
        product_snapshot_fragile=False,
        product_snapshot_stackable=True,
        product_snapshot_rotation_allowed=True,
        placed=placed,
        **placement_values,
    )


def make_plan(
    *,
    items: list[LoadPlanItem] | None = None,
    status: str = "CALCULATED",
    recalculated_from_id: uuid.UUID | None = SOURCE_PLAN_ID,
    approved_at: datetime | None = None,
) -> LoadPlan:
    plan_items = items or [make_item(suffix=1)]
    loaded_count = sum(item.placed for item in plan_items)
    unloaded_count = len(plan_items) - loaded_count
    used_volume_cm3 = loaded_count * 6_000
    total_weight_kg = Decimal("12.500") * loaded_count
    occupancy_percent = Decimal(used_volume_cm3) / Decimal(10000)

    order_ids = {item.order_id for item in plan_items}
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
        occupancy_percent=occupancy_percent,
        total_weight_kg=total_weight_kg,
        loaded_count=loaded_count,
        unloaded_count=unloaded_count,
        algorithm_version="heuristic-v1",
        created_at=datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc),
        approved_at=approved_at,
        orders=[
            LoadPlanOrder(load_plan_id=PLAN_ID, order_id=order_id)
            for order_id in sorted(order_ids, key=lambda identifier: -identifier.int)
        ],
        items=plan_items,
    )


def test_load_plan_create_accepts_distinct_order_ids() -> None:
    schema = LoadPlanCreate(
        truck_id=TRUCK_ID,
        order_ids=[FIRST_ORDER_ID, SECOND_ORDER_ID],
    )

    assert schema.truck_id == TRUCK_ID
    assert schema.order_ids == [FIRST_ORDER_ID, SECOND_ORDER_ID]


@pytest.mark.parametrize(
    "order_ids",
    [[], [FIRST_ORDER_ID, FIRST_ORDER_ID]],
)
def test_load_plan_create_rejects_empty_or_duplicate_order_ids(
    order_ids: list[uuid.UUID],
) -> None:
    with pytest.raises(ValidationError):
        LoadPlanCreate(truck_id=TRUCK_ID, order_ids=order_ids)


def test_map_load_plan_item_renames_flat_orm_snapshot_and_placement_fields() -> None:
    item = make_item(suffix=7, volume_index=2, loading_sequence=3)

    result = map_load_plan_item(item)

    assert result.id == item.id
    assert result.order_id == item.order_id
    assert result.order_item_id == item.order_item_id
    assert result.product_id == item.product_id
    assert result.volume_index == 2
    assert result.quantity == 2
    assert result.delivery_sequence == 2
    assert result.product_code == "PRODUCT-7"
    assert result.product_name == "Produto 7"
    assert (
        result.original_width_cm,
        result.original_height_cm,
        result.original_length_cm,
    ) == (10, 20, 30)
    assert result.weight_kg == Decimal("12.500")
    assert isinstance(result.weight_kg, Decimal)
    assert result.fragile is False
    assert result.stackable is True
    assert result.rotation_allowed is True
    assert (result.x_cm, result.y_cm, result.z_cm) == (7, 0, 14)
    assert (result.width_cm, result.height_cm, result.length_cm) == (10, 20, 30)
    assert result.rotation_code == "XYZ"
    assert result.loading_sequence == 3
    assert result.placed is True
    assert result.rejection_reason is None


def test_load_plan_item_read_enforces_placed_and_unloaded_shapes() -> None:
    placed_payload = map_load_plan_item(make_item(suffix=1)).model_dump()
    placed_payload["x_cm"] = None

    with pytest.raises(ValidationError, match="all placement fields"):
        LoadPlanItemRead.model_validate(placed_payload)

    unloaded_payload = map_load_plan_item(
        make_item(suffix=2, placed=False)
    ).model_dump()
    unloaded_payload["width_cm"] = 10

    with pytest.raises(ValidationError, match="must not include placement fields"):
        LoadPlanItemRead.model_validate(unloaded_payload)


def test_load_plan_item_read_enforces_rejection_reason_exclusivity() -> None:
    placed_payload = map_load_plan_item(make_item(suffix=1)).model_dump()
    placed_payload["rejection_reason"] = "COLLISION"

    with pytest.raises(ValidationError, match="must not include rejection_reason"):
        LoadPlanItemRead.model_validate(placed_payload)

    unloaded_payload = map_load_plan_item(
        make_item(suffix=2, placed=False)
    ).model_dump()
    unloaded_payload["rejection_reason"] = None

    with pytest.raises(ValidationError, match="must include rejection_reason"):
        LoadPlanItemRead.model_validate(unloaded_payload)


def test_load_plan_item_read_rejects_index_above_snapshot_quantity() -> None:
    payload = map_load_plan_item(make_item(suffix=1)).model_dump()
    payload["volume_index"] = 3
    payload["quantity"] = 2

    with pytest.raises(ValidationError, match="must not exceed quantity"):
        LoadPlanItemRead.model_validate(payload)


def test_map_load_plan_read_maps_lineage_metrics_ids_and_enriched_items() -> None:
    second_order_item = make_item(
        suffix=2,
        order_id=SECOND_ORDER_ID,
        order_item_suffix=20,
        volume_index=2,
        loading_sequence=2,
    )
    first_order_item = make_item(
        suffix=1,
        order_id=FIRST_ORDER_ID,
        order_item_suffix=10,
        loading_sequence=1,
    )
    plan = make_plan(items=[second_order_item, first_order_item])

    result = map_load_plan_read(plan)

    assert result.id == PLAN_ID
    assert result.truck_id == TRUCK_ID
    assert result.recalculated_from_id == SOURCE_PLAN_ID
    assert result.status == "CALCULATED"
    assert result.internal_volume_cm3 == 1_000_000
    assert result.used_volume_cm3 == 12_000
    assert result.occupancy_percent == Decimal("1.2")
    assert result.total_weight_kg == Decimal("25.000")
    assert result.loaded_count == 2
    assert result.unloaded_count == 0
    assert result.algorithm_version == "heuristic-v1"
    assert result.created_at == datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    assert result.approved_at is None
    assert result.order_ids == [FIRST_ORDER_ID, SECOND_ORDER_ID]
    assert [item.order_item_id for item in result.items] == sorted(
        [second_order_item.order_item_id, first_order_item.order_item_id],
        key=lambda identifier: identifier.int,
    )
    assert all(isinstance(item, LoadPlanItemRead) for item in result.items)


def test_load_plan_read_rejects_counts_that_disagree_with_items() -> None:
    payload = map_load_plan_read(make_plan()).model_dump()
    payload["loaded_count"] = 0

    with pytest.raises(ValidationError, match="loaded_count must match"):
        LoadPlanRead.model_validate(payload)


def test_map_load_plan_read_accepts_rejected_plan_with_zero_metrics() -> None:
    plan = make_plan(
        items=[make_item(suffix=1, placed=False)],
        status="REJECTED",
    )

    result = map_load_plan_read(plan)

    assert result.status == "REJECTED"
    assert result.loaded_count == 0
    assert result.unloaded_count == 1
    assert result.used_volume_cm3 == 0
    assert result.total_weight_kg == Decimal("0.000")
    assert result.occupancy_percent == Decimal(0)


def test_load_plan_read_rejects_approved_plan_with_unloaded_items() -> None:
    plan = make_plan(
        items=[
            make_item(suffix=1),
            make_item(suffix=2, placed=False),
        ]
    )
    payload = map_load_plan_read(plan).model_dump()
    payload["status"] = "APPROVED"
    payload["approved_at"] = datetime(2026, 8, 4, 13, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="must not include unloaded items"):
        LoadPlanRead.model_validate(payload)


def test_map_visualization_uses_snapshot_and_orders_each_result_collection() -> None:
    placed_second = make_item(
        suffix=4,
        order_item_suffix=40,
        loading_sequence=2,
    )
    unloaded_later_identity = make_item(
        suffix=5,
        order_item_suffix=60,
        placed=False,
    )
    placed_first = make_item(
        suffix=3,
        order_item_suffix=30,
        loading_sequence=1,
    )
    unloaded_first_identity = make_item(
        suffix=6,
        order_item_suffix=50,
        placed=False,
        rejection_reason="TRUCK_WEIGHT_EXCEEDED",
    )
    plan = make_plan(
        items=[
            placed_second,
            unloaded_later_identity,
            placed_first,
            unloaded_first_identity,
        ]
    )

    result = map_load_plan_visualization(plan)

    assert set(result.model_dump()) == {"truck", "items", "unloaded_items"}
    assert result.truck.id == TRUCK_ID
    assert result.truck.plate == "ABC1D23"
    assert result.truck.model == "Baú médio"
    assert (
        result.truck.width_cm,
        result.truck.height_cm,
        result.truck.length_cm,
    ) == (100, 100, 100)
    assert result.truck.max_weight_kg == Decimal("8000.00")
    assert [item.loading_sequence for item in result.items] == [1, 2]
    assert [item.id for item in result.items] == [placed_first.id, placed_second.id]
    assert all(isinstance(item, PlacedLoadPlanItemRead) for item in result.items)
    assert [item.order_item_id for item in result.unloaded_items] == [
        unloaded_first_identity.order_item_id,
        unloaded_later_identity.order_item_id,
    ]
    assert all(
        isinstance(item, UnloadedLoadPlanItemRead) for item in result.unloaded_items
    )
    assert result.unloaded_items[0].rejection_reason == "TRUCK_WEIGHT_EXCEEDED"
    assert "placed" not in result.items[0].model_dump()
    assert "rejection_reason" not in result.items[0].model_dump()
    unloaded_payload = result.unloaded_items[0].model_dump()
    assert "placed" not in unloaded_payload
    assert "x_cm" not in unloaded_payload
    assert "rotation_code" not in unloaded_payload
