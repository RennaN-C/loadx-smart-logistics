import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.json_decimal import JsonDecimal
from app.modules.load_planning.schemas import LoadPlanRead, TruckSnapshotRead


class VolumeReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    order_item_id: uuid.UUID
    volume_index: int = Field(gt=0)


class DistributionNeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def distinct_orders(self) -> Self:
        if len(set(self.order_ids)) != len(self.order_ids):
            raise ValueError("order_ids must be distinct")
        return self


class DistributionPartCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truck_id: uuid.UUID
    volumes: list[VolumeReference] = Field(min_length=1, max_length=200)


class DistributionCreate(DistributionNeedRequest):
    parts: list[DistributionPartCreate] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def distinct_partition(self) -> Self:
        trucks = [part.truck_id for part in self.parts]
        volumes = [volume for part in self.parts for volume in part.volumes]
        if len(set(trucks)) != len(trucks):
            raise ValueError("trucks must be distinct")
        if len(set(volumes)) != len(volumes) or len(volumes) > 200:
            raise ValueError("volumes must be distinct and at most 200")
        return self


class DistributionPartReprocess(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truck_id: uuid.UUID
    expected_load_plan_id: uuid.UUID


class DistributionAction(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DistributionVolumeRead(VolumeReference):
    order_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    part_id: uuid.UUID


class DistributionPartRead(BaseModel):
    id: uuid.UUID
    status: Literal["PENDING", "APPROVED", "CANCELED"]
    load_plan: LoadPlanRead


class DistributionRead(BaseModel):
    id: uuid.UUID
    status: Literal[
        "PROPOSED", "PARTIALLY_APPROVED", "APPROVED", "INCOMPLETE", "CANCELED"
    ]
    created_by: uuid.UUID
    created_at: datetime
    order_ids: list[uuid.UUID]
    truck_count: int
    volume_count: int
    parts: list[DistributionPartRead]
    volumes: list[DistributionVolumeRead]


class NeedVolumeRead(VolumeReference):
    order_id: uuid.UUID
    product_id: uuid.UUID
    width_cm: int
    height_cm: int
    length_cm: int
    weight_kg: JsonDecimal
    delivery_sequence: int
    fragile: bool
    stackable: bool
    rotation_allowed: bool


class IneligibleTruckRead(BaseModel):
    truck_id: uuid.UUID
    reason: Literal["INACTIVE", "TRUCK_OPERATION_CONFLICT", "TRUCK_IN_MAINTENANCE"]


class DistributionNeedRead(BaseModel):
    order_ids: list[uuid.UUID]
    volumes: list[NeedVolumeRead]
    eligible_trucks: list[TruckSnapshotRead]
    ineligible_trucks: list[IneligibleTruckRead]
