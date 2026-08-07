"""create load planning tables

Revision ID: 20260804_0004
Revises: 20260730_0003
Create Date: 2026-08-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0004"
down_revision: str | None = "20260730_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "load_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("truck_id", sa.Uuid(), nullable=False),
        sa.Column("recalculated_from_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("truck_snapshot_plate", sa.String(length=16), nullable=False),
        sa.Column("truck_snapshot_model", sa.String(length=120), nullable=False),
        sa.Column("truck_snapshot_internal_width_cm", sa.Integer(), nullable=False),
        sa.Column("truck_snapshot_internal_height_cm", sa.Integer(), nullable=False),
        sa.Column("truck_snapshot_internal_length_cm", sa.Integer(), nullable=False),
        sa.Column(
            "truck_snapshot_max_weight_kg",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
        ),
        sa.Column("internal_volume_cm3", sa.BigInteger(), nullable=False),
        sa.Column("used_volume_cm3", sa.BigInteger(), nullable=False),
        sa.Column(
            "occupancy_percent",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
        sa.Column(
            "total_weight_kg",
            sa.Numeric(precision=11, scale=3),
            nullable=False,
        ),
        sa.Column("loaded_count", sa.Integer(), nullable=False),
        sa.Column("unloaded_count", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('CALCULATED', 'APPROVED', 'REJECTED')",
            name=op.f("ck_load_plans__status_allowed"),
        ),
        sa.CheckConstraint(
            "truck_snapshot_internal_width_cm > 0 "
            "AND truck_snapshot_internal_height_cm > 0 "
            "AND truck_snapshot_internal_length_cm > 0",
            name=op.f("ck_load_plans__truck_snapshot_dimensions_positive"),
        ),
        sa.CheckConstraint(
            "truck_snapshot_max_weight_kg > 0",
            name=op.f("ck_load_plans__truck_snapshot_max_weight_positive"),
        ),
        sa.CheckConstraint(
            "internal_volume_cm3 > 0 "
            "AND used_volume_cm3 >= 0 "
            "AND used_volume_cm3 <= internal_volume_cm3",
            name=op.f("ck_load_plans__volume_metrics_valid"),
        ),
        sa.CheckConstraint(
            "internal_volume_cm3 = "
            "CAST(truck_snapshot_internal_width_cm AS BIGINT) "
            "* CAST(truck_snapshot_internal_height_cm AS BIGINT) "
            "* CAST(truck_snapshot_internal_length_cm AS BIGINT)",
            name=op.f("ck_load_plans__internal_volume_matches_snapshot"),
        ),
        sa.CheckConstraint(
            "occupancy_percent >= 0 AND occupancy_percent <= 100",
            name=op.f("ck_load_plans__occupancy_percent_range"),
        ),
        sa.CheckConstraint(
            "total_weight_kg >= 0 AND total_weight_kg <= truck_snapshot_max_weight_kg",
            name=op.f("ck_load_plans__total_weight_valid"),
        ),
        sa.CheckConstraint(
            "loaded_count >= 0 "
            "AND unloaded_count >= 0 "
            "AND loaded_count + unloaded_count > 0",
            name=op.f("ck_load_plans__counts_valid"),
        ),
        sa.CheckConstraint(
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
            name=op.f("ck_load_plans__status_metrics_consistent"),
        ),
        sa.CheckConstraint(
            "(status = 'APPROVED' "
            "AND approved_at IS NOT NULL "
            "AND unloaded_count = 0) "
            "OR (status <> 'APPROVED' AND approved_at IS NULL)",
            name=op.f("ck_load_plans__approval_consistent"),
        ),
        sa.CheckConstraint(
            "recalculated_from_id IS NULL OR recalculated_from_id <> id",
            name=op.f("ck_load_plans__recalculation_not_self"),
        ),
        sa.CheckConstraint(
            "length(algorithm_version) > 0",
            name=op.f("ck_load_plans__algorithm_version_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["truck_id"],
            ["trucks.id"],
            name="fk_load_plans__trucks",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recalculated_from_id"],
            ["load_plans.id"],
            name="fk_load_plans__load_plans",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_load_plans"),
    )
    op.create_index(
        "ix_load_plans__recalculated_from_id",
        "load_plans",
        ["recalculated_from_id"],
        unique=False,
    )
    op.create_index("ix_load_plans__status", "load_plans", ["status"], unique=False)
    op.create_index("ix_load_plans__truck_id", "load_plans", ["truck_id"], unique=False)

    op.create_table(
        "load_plan_orders",
        sa.Column("load_plan_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["load_plan_id"],
            ["load_plans.id"],
            name="fk_load_plan_orders__load_plans",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_load_plan_orders__orders",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("load_plan_id", "order_id", name="pk_load_plan_orders"),
    )
    op.create_index(
        "ix_load_plan_orders__order_id",
        "load_plan_orders",
        ["order_id"],
        unique=False,
    )

    op.create_unique_constraint(
        "uq_order_items__id_order_product",
        "order_items",
        ["id", "order_id", "product_id"],
    )

    op.create_table(
        "load_plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("load_plan_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("volume_index", sa.Integer(), nullable=False),
        sa.Column("order_item_snapshot_quantity", sa.Integer(), nullable=False),
        sa.Column(
            "order_item_snapshot_delivery_sequence", sa.Integer(), nullable=False
        ),
        sa.Column("product_snapshot_code", sa.String(length=64), nullable=False),
        sa.Column("product_snapshot_name", sa.String(length=160), nullable=False),
        sa.Column("product_snapshot_width_cm", sa.Integer(), nullable=False),
        sa.Column("product_snapshot_height_cm", sa.Integer(), nullable=False),
        sa.Column("product_snapshot_length_cm", sa.Integer(), nullable=False),
        sa.Column(
            "product_snapshot_weight_kg",
            sa.Numeric(precision=10, scale=3),
            nullable=False,
        ),
        sa.Column("product_snapshot_fragile", sa.Boolean(), nullable=False),
        sa.Column("product_snapshot_stackable", sa.Boolean(), nullable=False),
        sa.Column("product_snapshot_rotation_allowed", sa.Boolean(), nullable=False),
        sa.Column("position_x_cm", sa.Integer(), nullable=True),
        sa.Column("position_y_cm", sa.Integer(), nullable=True),
        sa.Column("position_z_cm", sa.Integer(), nullable=True),
        sa.Column("used_width_cm", sa.Integer(), nullable=True),
        sa.Column("used_height_cm", sa.Integer(), nullable=True),
        sa.Column("used_length_cm", sa.Integer(), nullable=True),
        sa.Column("rotation_code", sa.String(length=3), nullable=True),
        sa.Column("loading_sequence", sa.Integer(), nullable=True),
        sa.Column("placed", sa.Boolean(), nullable=False),
        sa.Column("rejection_reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "volume_index > 0",
            name=op.f("ck_load_plan_items__volume_index_positive"),
        ),
        sa.CheckConstraint(
            "order_item_snapshot_quantity > 0 "
            "AND order_item_snapshot_delivery_sequence > 0",
            name=op.f("ck_load_plan_items__order_item_snapshot_values_positive"),
        ),
        sa.CheckConstraint(
            "volume_index <= order_item_snapshot_quantity",
            name=op.f("ck_load_plan_items__volume_index_within_snapshot_quantity"),
        ),
        sa.CheckConstraint(
            "product_snapshot_width_cm > 0 "
            "AND product_snapshot_height_cm > 0 "
            "AND product_snapshot_length_cm > 0 "
            "AND product_snapshot_weight_kg > 0",
            name=op.f("ck_load_plan_items__product_snapshot_values_positive"),
        ),
        sa.CheckConstraint(
            "rotation_code IS NULL "
            "OR rotation_code IN ('XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX')",
            name=op.f("ck_load_plan_items__rotation_code_allowed"),
        ),
        sa.CheckConstraint(
            "product_snapshot_rotation_allowed = true "
            "OR rotation_code IS NULL "
            "OR rotation_code = 'XYZ'",
            name=op.f("ck_load_plan_items__rotation_permission_consistent"),
        ),
        sa.CheckConstraint(
            "rejection_reason IS NULL "
            "OR rejection_reason IN ("
            "'TRUCK_DIMENSIONS_EXCEEDED', "
            "'TRUCK_WEIGHT_EXCEEDED', "
            "'NON_STACKABLE_SUPPORT', "
            "'FRAGILE_SUPPORT_WEIGHT_EXCEEDED', "
            "'INSUFFICIENT_SUPPORT', "
            "'COLLISION', "
            "'NO_VALID_POSITION')",
            name=op.f("ck_load_plan_items__rejection_reason_allowed"),
        ),
        sa.CheckConstraint(
            "position_x_cm IS NULL OR position_x_cm >= 0",
            name=op.f("ck_load_plan_items__position_x_non_negative"),
        ),
        sa.CheckConstraint(
            "position_y_cm IS NULL OR position_y_cm >= 0",
            name=op.f("ck_load_plan_items__position_y_non_negative"),
        ),
        sa.CheckConstraint(
            "position_z_cm IS NULL OR position_z_cm >= 0",
            name=op.f("ck_load_plan_items__position_z_non_negative"),
        ),
        sa.CheckConstraint(
            "used_width_cm IS NULL OR used_width_cm > 0",
            name=op.f("ck_load_plan_items__used_width_positive"),
        ),
        sa.CheckConstraint(
            "used_height_cm IS NULL OR used_height_cm > 0",
            name=op.f("ck_load_plan_items__used_height_positive"),
        ),
        sa.CheckConstraint(
            "used_length_cm IS NULL OR used_length_cm > 0",
            name=op.f("ck_load_plan_items__used_length_positive"),
        ),
        sa.CheckConstraint(
            "loading_sequence IS NULL OR loading_sequence > 0",
            name=op.f("ck_load_plan_items__loading_sequence_positive"),
        ),
        sa.CheckConstraint(
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
            name=op.f("ck_load_plan_items__rotation_dimensions_consistent"),
        ),
        sa.CheckConstraint(
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
            name=op.f("ck_load_plan_items__placed_or_rejected"),
        ),
        sa.ForeignKeyConstraint(
            ["load_plan_id", "order_id"],
            ["load_plan_orders.load_plan_id", "load_plan_orders.order_id"],
            name="fk_load_plan_items__load_plan_orders",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id", "order_id", "product_id"],
            ["order_items.id", "order_items.order_id", "order_items.product_id"],
            name="fk_load_plan_items__order_item_provenance",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["load_plan_id"],
            ["load_plans.id"],
            name="fk_load_plan_items__load_plans",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_load_plan_items__orders",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["order_items.id"],
            name="fk_load_plan_items__order_items",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_load_plan_items__products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_load_plan_items"),
        sa.UniqueConstraint(
            "load_plan_id",
            "order_item_id",
            "volume_index",
            name="uq_load_plan_items__plan_item_volume",
        ),
        sa.UniqueConstraint(
            "load_plan_id",
            "loading_sequence",
            name="uq_load_plan_items__plan_loading_sequence",
        ),
    )
    op.create_index(
        "ix_load_plan_items__load_plan_id",
        "load_plan_items",
        ["load_plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_load_plan_items__order_id",
        "load_plan_items",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_load_plan_items__order_item_id",
        "load_plan_items",
        ["order_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_load_plan_items__product_id",
        "load_plan_items",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_load_plan_items__product_id", table_name="load_plan_items")
    op.drop_index("ix_load_plan_items__order_item_id", table_name="load_plan_items")
    op.drop_index("ix_load_plan_items__order_id", table_name="load_plan_items")
    op.drop_index("ix_load_plan_items__load_plan_id", table_name="load_plan_items")
    op.drop_table("load_plan_items")
    op.drop_constraint(
        "uq_order_items__id_order_product",
        "order_items",
        type_="unique",
    )

    op.drop_index("ix_load_plan_orders__order_id", table_name="load_plan_orders")
    op.drop_table("load_plan_orders")

    op.drop_index("ix_load_plans__truck_id", table_name="load_plans")
    op.drop_index("ix_load_plans__status", table_name="load_plans")
    op.drop_index("ix_load_plans__recalculated_from_id", table_name="load_plans")
    op.drop_table("load_plans")
