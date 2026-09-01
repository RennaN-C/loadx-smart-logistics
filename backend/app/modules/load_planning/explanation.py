import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.modules.load_planning.models import (
    LOAD_PLAN_STATUS_VALUES,
    REJECTION_REASON_VALUES,
    ROTATION_CODE_VALUES,
    LoadPlan,
    LoadPlanItem,
)


@dataclass(frozen=True, slots=True)
class ExplanationTruckSnapshot:
    truck_id: uuid.UUID
    plate: str
    model: str
    internal_width_cm: int
    internal_height_cm: int
    internal_length_cm: int
    max_weight_kg: Decimal


@dataclass(frozen=True, slots=True)
class ExplanationVolumeSnapshot:
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    product_id: uuid.UUID
    volume_index: int
    quantity: int
    delivery_sequence: int
    product_code: str
    product_name: str
    original_width_cm: int
    original_height_cm: int
    original_length_cm: int
    weight_kg: Decimal
    fragile: bool
    stackable: bool
    rotation_allowed: bool


@dataclass(frozen=True, slots=True)
class ExplanationPlacedItem:
    volume: ExplanationVolumeSnapshot
    x_cm: int
    y_cm: int
    z_cm: int
    width_cm: int
    height_cm: int
    length_cm: int
    rotation_code: str
    loading_sequence: int


@dataclass(frozen=True, slots=True)
class ExplanationRejectedItem:
    volume: ExplanationVolumeSnapshot
    rejection_reason: str


@dataclass(frozen=True, slots=True)
class LoadPlanExplanationContext:
    load_plan_id: uuid.UUID
    recalculated_from_id: uuid.UUID | None
    status: str
    order_ids: tuple[uuid.UUID, ...]
    truck: ExplanationTruckSnapshot
    internal_volume_cm3: int
    used_volume_cm3: int
    occupancy_percent: Decimal
    total_weight_kg: Decimal
    loaded_count: int
    unloaded_count: int
    algorithm_version: str
    placed_items: tuple[ExplanationPlacedItem, ...]
    rejected_items: tuple[ExplanationRejectedItem, ...]


def _invalid(reason: str) -> ValueError:
    return ValueError(f"invalid persisted load plan for explanation: {reason}")


def _require_uuid(value: object, field_name: str) -> uuid.UUID:
    if not isinstance(value, uuid.UUID):
        raise _invalid(f"{field_name} must be a UUID")
    return value


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _invalid(f"{field_name} must be a non-empty string")
    return value


def _require_int(
    value: object,
    field_name: str,
    *,
    minimum: int,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise _invalid(f"{field_name} must be an integer >= {minimum}")
    return value


def _require_decimal(value: object, field_name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise _invalid(f"{field_name} must be a finite Decimal")
    return value


def _build_truck_snapshot(load_plan: LoadPlan) -> ExplanationTruckSnapshot:
    width_cm = _require_int(
        load_plan.truck_snapshot_internal_width_cm,
        "truck_snapshot_internal_width_cm",
        minimum=1,
    )
    height_cm = _require_int(
        load_plan.truck_snapshot_internal_height_cm,
        "truck_snapshot_internal_height_cm",
        minimum=1,
    )
    length_cm = _require_int(
        load_plan.truck_snapshot_internal_length_cm,
        "truck_snapshot_internal_length_cm",
        minimum=1,
    )
    max_weight_kg = _require_decimal(
        load_plan.truck_snapshot_max_weight_kg,
        "truck_snapshot_max_weight_kg",
    )
    if max_weight_kg <= 0:
        raise _invalid("truck_snapshot_max_weight_kg must be greater than zero")

    return ExplanationTruckSnapshot(
        truck_id=_require_uuid(load_plan.truck_id, "truck_id"),
        plate=_require_text(load_plan.truck_snapshot_plate, "truck_snapshot_plate"),
        model=_require_text(load_plan.truck_snapshot_model, "truck_snapshot_model"),
        internal_width_cm=width_cm,
        internal_height_cm=height_cm,
        internal_length_cm=length_cm,
        max_weight_kg=max_weight_kg,
    )


def _build_volume_snapshot(item: LoadPlanItem) -> ExplanationVolumeSnapshot:
    quantity = _require_int(
        item.order_item_snapshot_quantity,
        "order_item_snapshot_quantity",
        minimum=1,
    )
    volume_index = _require_int(item.volume_index, "volume_index", minimum=1)
    if volume_index > quantity:
        raise _invalid("volume_index must not exceed snapshot quantity")

    weight_kg = _require_decimal(
        item.product_snapshot_weight_kg,
        "product_snapshot_weight_kg",
    )
    if weight_kg <= 0:
        raise _invalid("product_snapshot_weight_kg must be greater than zero")

    for field_name in (
        "product_snapshot_fragile",
        "product_snapshot_stackable",
        "product_snapshot_rotation_allowed",
    ):
        if not isinstance(getattr(item, field_name), bool):
            raise _invalid(f"{field_name} must be a boolean")

    return ExplanationVolumeSnapshot(
        order_id=_require_uuid(item.order_id, "item.order_id"),
        order_item_id=_require_uuid(item.order_item_id, "item.order_item_id"),
        product_id=_require_uuid(item.product_id, "item.product_id"),
        volume_index=volume_index,
        quantity=quantity,
        delivery_sequence=_require_int(
            item.order_item_snapshot_delivery_sequence,
            "order_item_snapshot_delivery_sequence",
            minimum=1,
        ),
        product_code=_require_text(
            item.product_snapshot_code,
            "product_snapshot_code",
        ),
        product_name=_require_text(
            item.product_snapshot_name,
            "product_snapshot_name",
        ),
        original_width_cm=_require_int(
            item.product_snapshot_width_cm,
            "product_snapshot_width_cm",
            minimum=1,
        ),
        original_height_cm=_require_int(
            item.product_snapshot_height_cm,
            "product_snapshot_height_cm",
            minimum=1,
        ),
        original_length_cm=_require_int(
            item.product_snapshot_length_cm,
            "product_snapshot_length_cm",
            minimum=1,
        ),
        weight_kg=weight_kg,
        fragile=item.product_snapshot_fragile,
        stackable=item.product_snapshot_stackable,
        rotation_allowed=item.product_snapshot_rotation_allowed,
    )


def _build_placed_item(
    item: LoadPlanItem,
    volume: ExplanationVolumeSnapshot,
) -> ExplanationPlacedItem:
    if item.rejection_reason is not None:
        raise _invalid("placed item must not include rejection_reason")

    rotation_code = item.rotation_code
    if rotation_code not in ROTATION_CODE_VALUES:
        raise _invalid("placed item must include an allowed rotation_code")
    if not volume.rotation_allowed and rotation_code != "XYZ":
        raise _invalid("placed item rotation conflicts with its snapshot permission")

    return ExplanationPlacedItem(
        volume=volume,
        x_cm=_require_int(item.position_x_cm, "position_x_cm", minimum=0),
        y_cm=_require_int(item.position_y_cm, "position_y_cm", minimum=0),
        z_cm=_require_int(item.position_z_cm, "position_z_cm", minimum=0),
        width_cm=_require_int(item.used_width_cm, "used_width_cm", minimum=1),
        height_cm=_require_int(item.used_height_cm, "used_height_cm", minimum=1),
        length_cm=_require_int(item.used_length_cm, "used_length_cm", minimum=1),
        rotation_code=rotation_code,
        loading_sequence=_require_int(
            item.loading_sequence,
            "loading_sequence",
            minimum=1,
        ),
    )


def _build_rejected_item(
    item: LoadPlanItem,
    volume: ExplanationVolumeSnapshot,
) -> ExplanationRejectedItem:
    placement_values = (
        item.position_x_cm,
        item.position_y_cm,
        item.position_z_cm,
        item.used_width_cm,
        item.used_height_cm,
        item.used_length_cm,
        item.rotation_code,
        item.loading_sequence,
    )
    if any(value is not None for value in placement_values):
        raise _invalid("rejected item must not include placement data")
    if item.rejection_reason not in REJECTION_REASON_VALUES:
        raise _invalid("rejected item must include an allowed rejection_reason")
    return ExplanationRejectedItem(
        volume=volume,
        rejection_reason=item.rejection_reason,
    )


def _resolve_recalculated_from(
    load_plan: LoadPlan,
    load_plan_id: uuid.UUID,
) -> uuid.UUID | None:
    recalculated_from_id = load_plan.recalculated_from_id
    if recalculated_from_id is None:
        return None

    recalculated_from_id = _require_uuid(recalculated_from_id, "recalculated_from_id")
    if recalculated_from_id == load_plan_id:
        raise _invalid("recalculated_from_id must differ from load_plan.id")
    return recalculated_from_id


def _require_status(load_plan: LoadPlan) -> str:
    if load_plan.status not in LOAD_PLAN_STATUS_VALUES:
        raise _invalid("status is not allowed")
    return load_plan.status


def _collect_order_ids(
    load_plan: LoadPlan,
    load_plan_id: uuid.UUID,
) -> tuple[uuid.UUID, ...]:
    order_ids: list[uuid.UUID] = []
    for association in tuple(load_plan.orders):
        if association.load_plan_id != load_plan_id:
            raise _invalid("order association references another load plan")
        order_ids.append(_require_uuid(association.order_id, "order_id"))

    if not order_ids:
        raise _invalid("at least one order_id is required")
    if len(set(order_ids)) != len(order_ids):
        raise _invalid("order_ids must not contain duplicates")

    return tuple(sorted(order_ids, key=lambda value: value.int))


def _partition_plan_items(
    load_plan: LoadPlan,
    load_plan_id: uuid.UUID,
    order_id_set: set[uuid.UUID],
) -> tuple[list[ExplanationPlacedItem], list[ExplanationRejectedItem]]:
    placed_items: list[ExplanationPlacedItem] = []
    rejected_items: list[ExplanationRejectedItem] = []
    identities: set[tuple[uuid.UUID, int]] = set()

    for item in tuple(load_plan.items):
        if item.load_plan_id != load_plan_id:
            raise _invalid("item references another load plan")
        volume = _build_volume_snapshot(item)
        if volume.order_id not in order_id_set:
            raise _invalid("item order_id is absent from plan order_ids")
        identity = (volume.order_item_id, volume.volume_index)
        if identity in identities:
            raise _invalid("volume identities must be unique")
        identities.add(identity)

        if item.placed is True:
            placed_items.append(_build_placed_item(item, volume))
        elif item.placed is False:
            rejected_items.append(_build_rejected_item(item, volume))
        else:
            raise _invalid("item.placed must be a boolean")

    if not identities:
        raise _invalid("at least one volume is required")

    placed_items.sort(
        key=lambda item: (
            item.loading_sequence,
            item.volume.order_item_id.int,
            item.volume.volume_index,
        )
    )
    rejected_items.sort(
        key=lambda item: (
            item.volume.order_item_id.int,
            item.volume.volume_index,
        )
    )
    return placed_items, rejected_items


def _validate_loading_sequences(placed_items: list[ExplanationPlacedItem]) -> None:
    loading_sequences = [item.loading_sequence for item in placed_items]
    if loading_sequences != list(range(1, len(placed_items) + 1)):
        raise _invalid("placed loading_sequence values must be contiguous")


def _validate_persisted_counts(
    load_plan: LoadPlan,
    placed_items: list[ExplanationPlacedItem],
    rejected_items: list[ExplanationRejectedItem],
) -> tuple[int, int]:
    loaded_count = _require_int(load_plan.loaded_count, "loaded_count", minimum=0)
    unloaded_count = _require_int(
        load_plan.unloaded_count,
        "unloaded_count",
        minimum=0,
    )
    if loaded_count != len(placed_items) or unloaded_count != len(rejected_items):
        raise _invalid("persisted counts must match placed and rejected items")
    return loaded_count, unloaded_count


def _validate_plan_metrics(
    load_plan: LoadPlan,
    truck: ExplanationTruckSnapshot,
) -> tuple[int, int, Decimal, Decimal]:
    internal_volume_cm3 = _require_int(
        load_plan.internal_volume_cm3,
        "internal_volume_cm3",
        minimum=1,
    )
    expected_internal_volume_cm3 = (
        truck.internal_width_cm * truck.internal_height_cm * truck.internal_length_cm
    )
    if internal_volume_cm3 != expected_internal_volume_cm3:
        raise _invalid("internal volume must match the truck snapshot")

    used_volume_cm3 = _require_int(
        load_plan.used_volume_cm3,
        "used_volume_cm3",
        minimum=0,
    )
    if used_volume_cm3 > internal_volume_cm3:
        raise _invalid("used_volume_cm3 must not exceed internal_volume_cm3")

    occupancy_percent = _require_decimal(
        load_plan.occupancy_percent,
        "occupancy_percent",
    )
    if occupancy_percent < 0 or occupancy_percent > 100:
        raise _invalid("occupancy_percent must be between zero and 100")

    total_weight_kg = _require_decimal(
        load_plan.total_weight_kg,
        "total_weight_kg",
    )
    if total_weight_kg < 0 or total_weight_kg > truck.max_weight_kg:
        raise _invalid("total_weight_kg must be within truck capacity")

    return internal_volume_cm3, used_volume_cm3, occupancy_percent, total_weight_kg


def _validate_status_consistency(
    status: str,
    placed_items: list[ExplanationPlacedItem],
    rejected_items: list[ExplanationRejectedItem],
    used_volume_cm3: int,
    occupancy_percent: Decimal,
    total_weight_kg: Decimal,
) -> None:
    if status == "REJECTED":
        if placed_items or used_volume_cm3 != 0 or total_weight_kg != 0:
            raise _invalid("rejected plan must have no placed volume metrics")
        if occupancy_percent != 0:
            raise _invalid("rejected plan occupancy_percent must be zero")
    elif not placed_items or used_volume_cm3 <= 0 or total_weight_kg <= 0:
        raise _invalid("calculated or approved plan must include placed volumes")

    if status == "APPROVED" and rejected_items:
        raise _invalid("approved plan must not include rejected items")


def build_load_plan_explanation_context(
    load_plan: LoadPlan,
) -> LoadPlanExplanationContext:
    """Copy an eagerly loaded persisted plan into a provider-neutral context.

    The caller must load ``orders`` and ``items`` before crossing a session
    boundary. ``LoadPlanRepository.get`` already guarantees that aggregate shape.

    This function only orchestrates. Each validation step lives in its own
    helper above, and the ORDER of the calls below is part of the contract: it
    decides which error a malformed plan reports first.
    """

    if not isinstance(load_plan, LoadPlan):
        raise TypeError("load_plan must be a persisted LoadPlan")

    load_plan_id = _require_uuid(load_plan.id, "load_plan.id")
    recalculated_from_id = _resolve_recalculated_from(load_plan, load_plan_id)
    status = _require_status(load_plan)

    sorted_order_ids = _collect_order_ids(load_plan, load_plan_id)
    placed_items, rejected_items = _partition_plan_items(
        load_plan,
        load_plan_id,
        set(sorted_order_ids),
    )
    _validate_loading_sequences(placed_items)
    loaded_count, unloaded_count = _validate_persisted_counts(
        load_plan,
        placed_items,
        rejected_items,
    )

    truck = _build_truck_snapshot(load_plan)
    (
        internal_volume_cm3,
        used_volume_cm3,
        occupancy_percent,
        total_weight_kg,
    ) = _validate_plan_metrics(load_plan, truck)
    _validate_status_consistency(
        status,
        placed_items,
        rejected_items,
        used_volume_cm3,
        occupancy_percent,
        total_weight_kg,
    )

    return LoadPlanExplanationContext(
        load_plan_id=load_plan_id,
        recalculated_from_id=recalculated_from_id,
        status=status,
        order_ids=sorted_order_ids,
        truck=truck,
        internal_volume_cm3=internal_volume_cm3,
        used_volume_cm3=used_volume_cm3,
        occupancy_percent=occupancy_percent,
        total_weight_kg=total_weight_kg,
        loaded_count=loaded_count,
        unloaded_count=unloaded_count,
        algorithm_version=_require_text(
            load_plan.algorithm_version,
            "algorithm_version",
        ),
        placed_items=tuple(placed_items),
        rejected_items=tuple(rejected_items),
    )
