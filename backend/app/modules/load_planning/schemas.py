import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.json_decimal import JsonDecimal
from app.modules.load_planning.models import LoadPlan, LoadPlanItem
from app.modules.load_planning.optimizer.comparison import TruckComparisonResult
from app.modules.load_planning.optimizer.rejections import (
    REJECTION_REASON_PRECEDENCE,
)

LoadPlanStatus = Literal["CALCULATED", "APPROVED", "REJECTED"]
RotationCodeValue = Literal["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]
RejectionReasonValue = Literal[
    "TRUCK_DIMENSIONS_EXCEEDED",
    "TRUCK_WEIGHT_EXCEEDED",
    "NON_STACKABLE_SUPPORT",
    "FRAGILE_SUPPORT_WEIGHT_EXCEEDED",
    "INSUFFICIENT_SUPPORT",
    "COLLISION",
    "NO_VALID_POSITION",
]


class LoadPlanCreate(BaseModel):
    truck_id: uuid.UUID
    order_ids: list[uuid.UUID] = Field(min_length=1)

    @field_validator("order_ids")
    @classmethod
    def require_distinct_order_ids(
        cls,
        order_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        if len(set(order_ids)) != len(order_ids):
            raise ValueError("order_ids must not contain duplicates")
        return order_ids


class TruckComparisonCreate(BaseModel):
    order_ids: list[uuid.UUID] = Field(min_length=1)
    truck_ids: list[uuid.UUID] = Field(min_length=2, max_length=10)

    @field_validator("order_ids", "truck_ids")
    @classmethod
    def require_distinct_ids(
        cls,
        identifiers: list[uuid.UUID],
        info: object,
    ) -> list[uuid.UUID]:
        if len(set(identifiers)) != len(identifiers):
            field_name = getattr(info, "field_name", "identifiers")
            raise ValueError(f"{field_name} must not contain duplicates")
        return identifiers


class TruckComparisonRead(BaseModel):
    truck_id: uuid.UUID
    internal_volume_cm3: int = Field(gt=0)
    used_volume_cm3: int = Field(ge=0)
    occupancy_percent: JsonDecimal = Field(ge=0, le=100, decimal_places=2)
    total_weight_kg: JsonDecimal = Field(ge=0, max_digits=11, decimal_places=3)
    loaded_count: int = Field(ge=0)
    unloaded_count: int = Field(ge=0)
    rejection_counts: dict[RejectionReasonValue, int]
    algorithm_version: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_comparison_metrics(self) -> Self:
        if self.used_volume_cm3 > self.internal_volume_cm3:
            raise ValueError("used_volume_cm3 must not exceed internal_volume_cm3")
        if any(count <= 0 for count in self.rejection_counts.values()):
            raise ValueError("rejection_counts must contain only positive counts")
        if sum(self.rejection_counts.values()) != self.unloaded_count:
            raise ValueError("rejection_counts must match unloaded_count")
        return self


LoadPlanExplanationSource = Literal["AI", "FALLBACK"]


class LoadPlanExplanationRead(BaseModel):
    load_plan_id: uuid.UUID
    source: LoadPlanExplanationSource
    explanation: str = Field(min_length=1)
    algorithm_version: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(str_strip_whitespace=True)


class _LoadPlanItemSnapshotRead(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    product_id: uuid.UUID
    volume_index: int = Field(gt=0)
    quantity: int = Field(gt=0)
    delivery_sequence: int = Field(gt=0)
    product_code: str = Field(min_length=1, max_length=64)
    product_name: str = Field(min_length=1, max_length=160)
    original_width_cm: int = Field(gt=0)
    original_height_cm: int = Field(gt=0)
    original_length_cm: int = Field(gt=0)
    weight_kg: JsonDecimal = Field(gt=0, max_digits=10, decimal_places=3)
    fragile: bool
    stackable: bool
    rotation_allowed: bool

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_volume_index_within_quantity(self) -> Self:
        if self.volume_index > self.quantity:
            raise ValueError("volume_index must not exceed quantity")
        return self


class LoadPlanItemRead(_LoadPlanItemSnapshotRead):
    x_cm: int | None = Field(default=None, ge=0)
    y_cm: int | None = Field(default=None, ge=0)
    z_cm: int | None = Field(default=None, ge=0)
    width_cm: int | None = Field(default=None, gt=0)
    height_cm: int | None = Field(default=None, gt=0)
    length_cm: int | None = Field(default=None, gt=0)
    rotation_code: RotationCodeValue | None = None
    loading_sequence: int | None = Field(default=None, gt=0)
    placed: bool
    rejection_reason: RejectionReasonValue | None = None

    @model_validator(mode="after")
    def validate_placement_shape(self) -> Self:
        placement_values = (
            self.x_cm,
            self.y_cm,
            self.z_cm,
            self.width_cm,
            self.height_cm,
            self.length_cm,
            self.rotation_code,
            self.loading_sequence,
        )
        if self.placed:
            if any(value is None for value in placement_values):
                raise ValueError("placed item must include all placement fields")
            if self.rejection_reason is not None:
                raise ValueError("placed item must not include rejection_reason")
        else:
            if any(value is not None for value in placement_values):
                raise ValueError("unloaded item must not include placement fields")
            if self.rejection_reason is None:
                raise ValueError("unloaded item must include rejection_reason")
        return self


class PlacedLoadPlanItemRead(_LoadPlanItemSnapshotRead):
    x_cm: int = Field(ge=0)
    y_cm: int = Field(ge=0)
    z_cm: int = Field(ge=0)
    width_cm: int = Field(gt=0)
    height_cm: int = Field(gt=0)
    length_cm: int = Field(gt=0)
    rotation_code: RotationCodeValue
    loading_sequence: int = Field(gt=0)


class UnloadedLoadPlanItemRead(_LoadPlanItemSnapshotRead):
    rejection_reason: RejectionReasonValue


class LoadPlanRead(BaseModel):
    id: uuid.UUID
    truck_id: uuid.UUID
    recalculated_from_id: uuid.UUID | None
    status: LoadPlanStatus
    internal_volume_cm3: int = Field(gt=0)
    used_volume_cm3: int = Field(ge=0)
    occupancy_percent: JsonDecimal = Field(ge=0, le=100, decimal_places=2)
    total_weight_kg: JsonDecimal = Field(ge=0, max_digits=11, decimal_places=3)
    loaded_count: int = Field(ge=0)
    unloaded_count: int = Field(ge=0)
    algorithm_version: str = Field(min_length=1, max_length=64)
    created_at: datetime
    approved_at: datetime | None
    order_ids: list[uuid.UUID] = Field(min_length=1)
    items: list[LoadPlanItemRead] = Field(min_length=1)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_plan_shape(self) -> Self:
        if self.recalculated_from_id == self.id:
            raise ValueError("recalculated_from_id must differ from id")
        if len(set(self.order_ids)) != len(self.order_ids):
            raise ValueError("order_ids must not contain duplicates")

        item_ids = [item.id for item in self.items]
        identities = [(item.order_item_id, item.volume_index) for item in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("items must not contain duplicate ids")
        if len(set(identities)) != len(identities):
            raise ValueError("items must not contain duplicate volume identities")
        order_id_set = set(self.order_ids)
        if any(item.order_id not in order_id_set for item in self.items):
            raise ValueError("every item order_id must be present in order_ids")

        actual_loaded_count = sum(item.placed for item in self.items)
        actual_unloaded_count = len(self.items) - actual_loaded_count
        if self.loaded_count != actual_loaded_count:
            raise ValueError("loaded_count must match placed items")
        if self.unloaded_count != actual_unloaded_count:
            raise ValueError("unloaded_count must match unloaded items")
        if self.used_volume_cm3 > self.internal_volume_cm3:
            raise ValueError("used_volume_cm3 must not exceed internal_volume_cm3")

        if self.status == "APPROVED":
            if self.approved_at is None:
                raise ValueError("approved plan must include approved_at")
            if self.unloaded_count != 0:
                raise ValueError("approved plan must not include unloaded items")
        elif self.approved_at is not None:
            raise ValueError("non-approved plan must not include approved_at")

        if self.status == "REJECTED":
            if self.loaded_count != 0:
                raise ValueError("rejected plan must not include placed items")
            if (
                self.used_volume_cm3 != 0
                or self.total_weight_kg != 0
                or self.occupancy_percent != 0
            ):
                raise ValueError("rejected plan metrics must be zero")
        if self.status in {"CALCULATED", "APPROVED"} and self.loaded_count == 0:
            raise ValueError("calculated or approved plan must include placed items")
        return self


class TruckSnapshotRead(BaseModel):
    id: uuid.UUID
    plate: str = Field(min_length=1, max_length=16)
    model: str = Field(min_length=1, max_length=120)
    width_cm: int = Field(gt=0)
    height_cm: int = Field(gt=0)
    length_cm: int = Field(gt=0)
    max_weight_kg: JsonDecimal = Field(gt=0, max_digits=10, decimal_places=2)

    model_config = ConfigDict(str_strip_whitespace=True)


class LoadPlanVisualizationRead(BaseModel):
    truck: TruckSnapshotRead
    items: list[PlacedLoadPlanItemRead]
    unloaded_items: list[UnloadedLoadPlanItemRead]


def map_load_plan_item(item: LoadPlanItem) -> LoadPlanItemRead:
    return LoadPlanItemRead(
        id=item.id,
        order_id=item.order_id,
        order_item_id=item.order_item_id,
        product_id=item.product_id,
        volume_index=item.volume_index,
        quantity=item.order_item_snapshot_quantity,
        delivery_sequence=item.order_item_snapshot_delivery_sequence,
        product_code=item.product_snapshot_code,
        product_name=item.product_snapshot_name,
        original_width_cm=item.product_snapshot_width_cm,
        original_height_cm=item.product_snapshot_height_cm,
        original_length_cm=item.product_snapshot_length_cm,
        weight_kg=item.product_snapshot_weight_kg,
        fragile=item.product_snapshot_fragile,
        stackable=item.product_snapshot_stackable,
        rotation_allowed=item.product_snapshot_rotation_allowed,
        x_cm=item.position_x_cm,
        y_cm=item.position_y_cm,
        z_cm=item.position_z_cm,
        width_cm=item.used_width_cm,
        height_cm=item.used_height_cm,
        length_cm=item.used_length_cm,
        rotation_code=item.rotation_code,
        loading_sequence=item.loading_sequence,
        placed=item.placed,
        rejection_reason=item.rejection_reason,
    )


def _identity_key(item: LoadPlanItemRead) -> tuple[int, int]:
    return (item.order_item_id.int, item.volume_index)


def map_load_plan_read(load_plan: LoadPlan) -> LoadPlanRead:
    items = sorted(
        (map_load_plan_item(item) for item in load_plan.items),
        key=_identity_key,
    )
    order_ids = sorted(
        (association.order_id for association in load_plan.orders),
        key=lambda order_id: order_id.int,
    )
    return LoadPlanRead(
        id=load_plan.id,
        truck_id=load_plan.truck_id,
        recalculated_from_id=load_plan.recalculated_from_id,
        status=load_plan.status,
        internal_volume_cm3=load_plan.internal_volume_cm3,
        used_volume_cm3=load_plan.used_volume_cm3,
        occupancy_percent=load_plan.occupancy_percent,
        total_weight_kg=load_plan.total_weight_kg,
        loaded_count=load_plan.loaded_count,
        unloaded_count=load_plan.unloaded_count,
        algorithm_version=load_plan.algorithm_version,
        created_at=load_plan.created_at,
        approved_at=load_plan.approved_at,
        order_ids=order_ids,
        items=items,
    )


def map_load_plan_visualization(load_plan: LoadPlan) -> LoadPlanVisualizationRead:
    mapped_items = tuple(map_load_plan_item(item) for item in load_plan.items)
    placed_items = sorted(
        (item for item in mapped_items if item.placed),
        key=lambda item: (
            item.loading_sequence,
            item.order_item_id.int,
            item.volume_index,
        ),
    )
    unloaded_items = sorted(
        (item for item in mapped_items if not item.placed),
        key=_identity_key,
    )

    return LoadPlanVisualizationRead(
        truck=TruckSnapshotRead(
            id=load_plan.truck_id,
            plate=load_plan.truck_snapshot_plate,
            model=load_plan.truck_snapshot_model,
            width_cm=load_plan.truck_snapshot_internal_width_cm,
            height_cm=load_plan.truck_snapshot_internal_height_cm,
            length_cm=load_plan.truck_snapshot_internal_length_cm,
            max_weight_kg=load_plan.truck_snapshot_max_weight_kg,
        ),
        items=[
            PlacedLoadPlanItemRead.model_validate(
                item.model_dump(exclude={"placed", "rejection_reason"})
            )
            for item in placed_items
        ],
        unloaded_items=[
            UnloadedLoadPlanItemRead.model_validate(
                item.model_dump(
                    exclude={
                        "x_cm",
                        "y_cm",
                        "z_cm",
                        "width_cm",
                        "height_cm",
                        "length_cm",
                        "rotation_code",
                        "loading_sequence",
                        "placed",
                    }
                )
            )
            for item in unloaded_items
        ],
    )


def map_truck_comparison(
    comparison: TruckComparisonResult,
) -> TruckComparisonRead:
    result = comparison.load_plan
    metrics = result.metrics
    rejection_counts = {
        reason.value: sum(
            rejected.rejection_reason == reason for rejected in result.rejected_volumes
        )
        for reason in REJECTION_REASON_PRECEDENCE
    }
    return TruckComparisonRead(
        truck_id=comparison.truck_id,
        internal_volume_cm3=metrics.internal_volume_cm3,
        used_volume_cm3=metrics.used_volume_cm3,
        occupancy_percent=metrics.occupancy_percent,
        total_weight_kg=metrics.total_weight_kg,
        loaded_count=metrics.loaded_count,
        unloaded_count=metrics.unloaded_count,
        rejection_counts={
            reason: count for reason, count in rejection_counts.items() if count > 0
        },
        algorithm_version=metrics.algorithm_version,
    )
