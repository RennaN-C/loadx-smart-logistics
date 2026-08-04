import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

LOAD_PLAN_STATUS_VALUES = ("CALCULATED", "APPROVED", "REJECTED")
ROTATION_CODE_VALUES = ("XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX")
REJECTION_REASON_VALUES = (
    "TRUCK_DIMENSIONS_EXCEEDED",
    "TRUCK_WEIGHT_EXCEEDED",
    "NON_STACKABLE_SUPPORT",
    "FRAGILE_SUPPORT_WEIGHT_EXCEEDED",
    "INSUFFICIENT_SUPPORT",
    "COLLISION",
    "NO_VALID_POSITION",
)


class LoadPlan(Base):
    __tablename__ = "load_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('CALCULATED', 'APPROVED', 'REJECTED')",
            name="status_allowed",
        ),
        CheckConstraint(
            "truck_snapshot_internal_width_cm > 0 "
            "AND truck_snapshot_internal_height_cm > 0 "
            "AND truck_snapshot_internal_length_cm > 0",
            name="truck_snapshot_dimensions_positive",
        ),
        CheckConstraint(
            "truck_snapshot_max_weight_kg > 0",
            name="truck_snapshot_max_weight_positive",
        ),
        CheckConstraint(
            "internal_volume_cm3 > 0 "
            "AND used_volume_cm3 >= 0 "
            "AND used_volume_cm3 <= internal_volume_cm3",
            name="volume_metrics_valid",
        ),
        CheckConstraint(
            "internal_volume_cm3 = "
            "CAST(truck_snapshot_internal_width_cm AS BIGINT) "
            "* CAST(truck_snapshot_internal_height_cm AS BIGINT) "
            "* CAST(truck_snapshot_internal_length_cm AS BIGINT)",
            name="internal_volume_matches_snapshot",
        ),
        CheckConstraint(
            "occupancy_percent >= 0 AND occupancy_percent <= 100",
            name="occupancy_percent_range",
        ),
        CheckConstraint(
            "total_weight_kg >= 0 "
            "AND total_weight_kg <= truck_snapshot_max_weight_kg",
            name="total_weight_valid",
        ),
        CheckConstraint(
            "loaded_count >= 0 "
            "AND unloaded_count >= 0 "
            "AND loaded_count + unloaded_count > 0",
            name="counts_valid",
        ),
        CheckConstraint(
            "(status = 'REJECTED' "
            "AND loaded_count = 0 "
            "AND unloaded_count > 0 "
            "AND used_volume_cm3 = 0 "
            "AND total_weight_kg = 0 "
            "AND occupancy_percent = 0) "
            "OR (status IN ('CALCULATED', 'APPROVED') "
            "AND loaded_count > 0 "
            "AND used_volume_cm3 > 0 "
            "AND total_weight_kg > 0)",
            name="status_metrics_consistent",
        ),
        CheckConstraint(
            "(status = 'APPROVED' "
            "AND approved_at IS NOT NULL "
            "AND unloaded_count = 0) "
            "OR (status <> 'APPROVED' AND approved_at IS NULL)",
            name="approval_consistent",
        ),
        CheckConstraint(
            "recalculated_from_id IS NULL OR recalculated_from_id <> id",
            name="recalculation_not_self",
        ),
        CheckConstraint(
            "length(algorithm_version) > 0",
            name="algorithm_version_not_empty",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    truck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trucks.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recalculated_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("load_plans.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    truck_snapshot_plate: Mapped[str] = mapped_column(String(16), nullable=False)
    truck_snapshot_model: Mapped[str] = mapped_column(String(120), nullable=False)
    truck_snapshot_internal_width_cm: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    truck_snapshot_internal_height_cm: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    truck_snapshot_internal_length_cm: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    truck_snapshot_max_weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )

    internal_volume_cm3: Mapped[int] = mapped_column(BigInteger, nullable=False)
    used_volume_cm3: Mapped[int] = mapped_column(BigInteger, nullable=False)
    occupancy_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(11, 3), nullable=False)
    loaded_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unloaded_count: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    recalculated_from: Mapped["LoadPlan | None"] = relationship(
        remote_side=[id],
        back_populates="recalculations",
    )
    recalculations: Mapped[list["LoadPlan"]] = relationship(
        back_populates="recalculated_from",
        passive_deletes="all",
    )
    orders: Mapped[list["LoadPlanOrder"]] = relationship(
        back_populates="load_plan",
        order_by="LoadPlanOrder.order_id",
    )
    items: Mapped[list["LoadPlanItem"]] = relationship(
        back_populates="load_plan",
        order_by="LoadPlanItem.order_item_id, LoadPlanItem.volume_index",
    )


class LoadPlanOrder(Base):
    __tablename__ = "load_plan_orders"

    load_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("load_plans.id", ondelete="RESTRICT"), primary_key=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), primary_key=True, index=True
    )

    load_plan: Mapped[LoadPlan] = relationship(back_populates="orders")


class LoadPlanItem(Base):
    __tablename__ = "load_plan_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ("load_plan_id", "order_id"),
            ("load_plan_orders.load_plan_id", "load_plan_orders.order_id"),
            name="fk_load_plan_items__load_plan_orders",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("order_item_id", "order_id", "product_id"),
            ("order_items.id", "order_items.order_id", "order_items.product_id"),
            name="fk_load_plan_items__order_item_provenance",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "load_plan_id",
            "order_item_id",
            "volume_index",
            name="uq_load_plan_items__plan_item_volume",
        ),
        UniqueConstraint(
            "load_plan_id",
            "loading_sequence",
            name="uq_load_plan_items__plan_loading_sequence",
        ),
        CheckConstraint("volume_index > 0", name="volume_index_positive"),
        CheckConstraint(
            "order_item_snapshot_quantity > 0 "
            "AND order_item_snapshot_delivery_sequence > 0",
            name="order_item_snapshot_values_positive",
        ),
        CheckConstraint(
            "volume_index <= order_item_snapshot_quantity",
            name="volume_index_within_snapshot_quantity",
        ),
        CheckConstraint(
            "product_snapshot_width_cm > 0 "
            "AND product_snapshot_height_cm > 0 "
            "AND product_snapshot_length_cm > 0 "
            "AND product_snapshot_weight_kg > 0",
            name="product_snapshot_values_positive",
        ),
        CheckConstraint(
            "rotation_code IS NULL "
            "OR rotation_code IN ('XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX')",
            name="rotation_code_allowed",
        ),
        CheckConstraint(
            "product_snapshot_rotation_allowed = true "
            "OR rotation_code IS NULL "
            "OR rotation_code = 'XYZ'",
            name="rotation_permission_consistent",
        ),
        CheckConstraint(
            "rejection_reason IS NULL "
            "OR rejection_reason IN ("
            "'TRUCK_DIMENSIONS_EXCEEDED', "
            "'TRUCK_WEIGHT_EXCEEDED', "
            "'NON_STACKABLE_SUPPORT', "
            "'FRAGILE_SUPPORT_WEIGHT_EXCEEDED', "
            "'INSUFFICIENT_SUPPORT', "
            "'COLLISION', "
            "'NO_VALID_POSITION')",
            name="rejection_reason_allowed",
        ),
        CheckConstraint(
            "position_x_cm IS NULL OR position_x_cm >= 0",
            name="position_x_non_negative",
        ),
        CheckConstraint(
            "position_y_cm IS NULL OR position_y_cm >= 0",
            name="position_y_non_negative",
        ),
        CheckConstraint(
            "position_z_cm IS NULL OR position_z_cm >= 0",
            name="position_z_non_negative",
        ),
        CheckConstraint(
            "used_width_cm IS NULL OR used_width_cm > 0",
            name="used_width_positive",
        ),
        CheckConstraint(
            "used_height_cm IS NULL OR used_height_cm > 0",
            name="used_height_positive",
        ),
        CheckConstraint(
            "used_length_cm IS NULL OR used_length_cm > 0",
            name="used_length_positive",
        ),
        CheckConstraint(
            "loading_sequence IS NULL OR loading_sequence > 0",
            name="loading_sequence_positive",
        ),
        CheckConstraint(
            "rotation_code IS NULL OR "
            "(rotation_code = 'XYZ' "
            "AND used_width_cm = product_snapshot_width_cm "
            "AND used_height_cm = product_snapshot_height_cm "
            "AND used_length_cm = product_snapshot_length_cm) OR "
            "(rotation_code = 'XZY' "
            "AND used_width_cm = product_snapshot_width_cm "
            "AND used_height_cm = product_snapshot_length_cm "
            "AND used_length_cm = product_snapshot_height_cm) OR "
            "(rotation_code = 'YXZ' "
            "AND used_width_cm = product_snapshot_height_cm "
            "AND used_height_cm = product_snapshot_width_cm "
            "AND used_length_cm = product_snapshot_length_cm) OR "
            "(rotation_code = 'YZX' "
            "AND used_width_cm = product_snapshot_height_cm "
            "AND used_height_cm = product_snapshot_length_cm "
            "AND used_length_cm = product_snapshot_width_cm) OR "
            "(rotation_code = 'ZXY' "
            "AND used_width_cm = product_snapshot_length_cm "
            "AND used_height_cm = product_snapshot_width_cm "
            "AND used_length_cm = product_snapshot_height_cm) OR "
            "(rotation_code = 'ZYX' "
            "AND used_width_cm = product_snapshot_length_cm "
            "AND used_height_cm = product_snapshot_height_cm "
            "AND used_length_cm = product_snapshot_width_cm)",
            name="rotation_dimensions_consistent",
        ),
        CheckConstraint(
            "(placed = true "
            "AND position_x_cm IS NOT NULL "
            "AND position_y_cm IS NOT NULL "
            "AND position_z_cm IS NOT NULL "
            "AND used_width_cm IS NOT NULL "
            "AND used_height_cm IS NOT NULL "
            "AND used_length_cm IS NOT NULL "
            "AND rotation_code IS NOT NULL "
            "AND loading_sequence IS NOT NULL "
            "AND rejection_reason IS NULL) "
            "OR (placed = false "
            "AND position_x_cm IS NULL "
            "AND position_y_cm IS NULL "
            "AND position_z_cm IS NULL "
            "AND used_width_cm IS NULL "
            "AND used_height_cm IS NULL "
            "AND used_length_cm IS NULL "
            "AND rotation_code IS NULL "
            "AND loading_sequence IS NULL "
            "AND rejection_reason IS NOT NULL)",
            name="placed_or_rejected",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    load_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("load_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    volume_index: Mapped[int] = mapped_column(Integer, nullable=False)

    order_item_snapshot_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_item_snapshot_delivery_sequence: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    product_snapshot_code: Mapped[str] = mapped_column(String(64), nullable=False)
    product_snapshot_name: Mapped[str] = mapped_column(String(160), nullable=False)
    product_snapshot_width_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    product_snapshot_height_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    product_snapshot_length_cm: Mapped[int] = mapped_column(Integer, nullable=False)
    product_snapshot_weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False
    )
    product_snapshot_fragile: Mapped[bool] = mapped_column(Boolean, nullable=False)
    product_snapshot_stackable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    product_snapshot_rotation_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )

    position_x_cm: Mapped[int | None] = mapped_column(Integer)
    position_y_cm: Mapped[int | None] = mapped_column(Integer)
    position_z_cm: Mapped[int | None] = mapped_column(Integer)
    used_width_cm: Mapped[int | None] = mapped_column(Integer)
    used_height_cm: Mapped[int | None] = mapped_column(Integer)
    used_length_cm: Mapped[int | None] = mapped_column(Integer)
    rotation_code: Mapped[str | None] = mapped_column(String(3))
    loading_sequence: Mapped[int | None] = mapped_column(Integer)
    placed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(64))

    load_plan: Mapped[LoadPlan] = relationship(back_populates="items")
