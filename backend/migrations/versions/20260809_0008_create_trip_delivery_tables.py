"""create trip and delivery tables

Revision ID: 20260809_0008
Revises: 20260809_0007
Create Date: 2026-08-09 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0008"
down_revision: str | None = "20260809_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        op.f("ck_status_history__entity_type_allowed"),
        "status_history",
        "entity_type IN ('ORDER', 'LOAD_PLAN', 'TRIP', 'DELIVERY')",
    )

    op.create_table(
        "trips",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("load_plan_id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="SCHEDULED",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'IN_ROUTE', 'FINISHED')",
            name=op.f("ck_trips__status_allowed"),
        ),
        sa.CheckConstraint(
            "(status = 'SCHEDULED' AND started_at IS NULL AND finished_at IS NULL) "
            "OR (status = 'IN_ROUTE' AND started_at IS NOT NULL "
            "AND finished_at IS NULL) "
            "OR (status = 'FINISHED' AND started_at IS NOT NULL "
            "AND finished_at IS NOT NULL AND finished_at >= started_at)",
            name=op.f("ck_trips__timestamps_consistent"),
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["drivers.id"],
            name=op.f("fk_trips__drivers"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["load_plan_id"],
            ["load_plans.id"],
            name=op.f("fk_trips__load_plans"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trips")),
        sa.UniqueConstraint(
            "load_plan_id",
            name=op.f("uq_trips__load_plan_id"),
        ),
    )
    op.create_index(
        op.f("ix_trips__driver_id"),
        "trips",
        ["driver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_trips__status"),
        "trips",
        ["status"],
        unique=False,
    )

    op.create_table(
        "deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'IN_DELIVERY', 'DELIVERED')",
            name=op.f("ck_deliveries__status_allowed"),
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name=op.f("ck_deliveries__sequence_positive"),
        ),
        sa.CheckConstraint(
            "(status = 'DELIVERED' AND delivered_at IS NOT NULL) "
            "OR (status <> 'DELIVERED' AND delivered_at IS NULL)",
            name=op.f("ck_deliveries__completion_consistent"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_deliveries__orders"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"],
            ["trips.id"],
            name=op.f("fk_deliveries__trips"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deliveries")),
        sa.UniqueConstraint(
            "order_id",
            name=op.f("uq_deliveries__order_id"),
        ),
        sa.UniqueConstraint(
            "trip_id",
            "order_id",
            name=op.f("uq_deliveries__trip_order"),
        ),
        sa.UniqueConstraint(
            "trip_id",
            "sequence",
            name=op.f("uq_deliveries__trip_sequence"),
        ),
    )
    op.create_index(
        op.f("ix_deliveries__order_id"),
        "deliveries",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deliveries__status"),
        "deliveries",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deliveries__trip_id"),
        "deliveries",
        ["trip_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_deliveries__trip_id"), table_name="deliveries")
    op.drop_index(op.f("ix_deliveries__status"), table_name="deliveries")
    op.drop_index(op.f("ix_deliveries__order_id"), table_name="deliveries")
    op.drop_table("deliveries")

    op.drop_index(op.f("ix_trips__status"), table_name="trips")
    op.drop_index(op.f("ix_trips__driver_id"), table_name="trips")
    op.drop_table("trips")

    op.drop_constraint(
        op.f("ck_status_history__entity_type_allowed"),
        "status_history",
        type_="check",
    )
