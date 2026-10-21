"""OC94 audited cancellation for scheduled trips and distribution parts.

Revision ID: 20261021_0032
Revises: 20261021_0031
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_0032"
down_revision: str | None = "20261021_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_trips__status_allowed", "trips", type_="check")
    op.drop_constraint("ck_trips__timestamps_consistent", "trips", type_="check")
    op.create_check_constraint(
        "ck_trips__status_allowed",
        "trips",
        "status IN ('SCHEDULED', 'IN_ROUTE', 'FINISHED', 'CANCELED')",
    )
    op.create_check_constraint(
        "ck_trips__timestamps_consistent",
        "trips",
        "(status IN ('SCHEDULED', 'CANCELED') AND started_at IS NULL "
        "AND finished_at IS NULL) OR "
        "(status = 'IN_ROUTE' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
        "(status = 'FINISHED' AND started_at IS NOT NULL "
        "AND finished_at IS NOT NULL AND finished_at >= started_at)",
    )

    op.drop_constraint("ck_deliveries__status_allowed", "deliveries", type_="check")
    op.create_check_constraint(
        "ck_deliveries__status_allowed",
        "deliveries",
        "status IN ('PENDING', 'IN_DELIVERY', 'DELIVERED', 'CANCELED')",
    )
    op.drop_index("uq_deliveries__legacy_order", table_name="deliveries")
    op.drop_constraint("uq_deliveries__part_order", "deliveries", type_="unique")
    op.create_index(
        "uq_deliveries__legacy_order",
        "deliveries",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text(
            "distribution_part_id IS NULL AND status <> 'CANCELED'"
        ),
    )
    op.create_index(
        "uq_deliveries__part_order",
        "deliveries",
        ["distribution_part_id", "order_id"],
        unique=True,
        postgresql_where=sa.text(
            "distribution_part_id IS NOT NULL AND status <> 'CANCELED'"
        ),
    )

    op.drop_constraint("ck_load_plans__status_allowed", "load_plans", type_="check")
    op.drop_constraint(
        "ck_load_plans__status_metrics_consistent", "load_plans", type_="check"
    )
    op.drop_constraint(
        "ck_load_plans__approval_consistent", "load_plans", type_="check"
    )
    op.create_check_constraint(
        "ck_load_plans__status_allowed",
        "load_plans",
        "status IN ('CALCULATED', 'APPROVED', 'REJECTED', 'CANCELED')",
    )
    op.create_check_constraint(
        "ck_load_plans__status_metrics_consistent",
        "load_plans",
        "(status = 'REJECTED' AND loaded_count = 0 AND unloaded_count > 0 "
        "AND used_volume_cm3 = 0 AND total_weight_kg = 0 "
        "AND occupancy_percent = 0) OR "
        "(status IN ('CALCULATED', 'APPROVED', 'CANCELED') "
        "AND loaded_count > 0 AND used_volume_cm3 > 0 "
        "AND total_weight_kg > 0)",
    )
    op.create_check_constraint(
        "ck_load_plans__approval_consistent",
        "load_plans",
        "(status IN ('APPROVED', 'CANCELED') AND approved_at IS NOT NULL "
        "AND unloaded_count = 0) OR "
        "(status NOT IN ('APPROVED', 'CANCELED') AND approved_at IS NULL)",
    )

    op.create_table(
        "trip_cancellations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "trip_id",
            sa.Uuid(),
            sa.ForeignKey("trips.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("trip_id", name="uq_trip_cancellations__trip"),
        sa.UniqueConstraint("idempotency_key", name="uq_trip_cancellations__request"),
    )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(sa.text("SELECT EXISTS (SELECT 1 FROM trip_cancellations)"))
        .scalar()
        or op.get_bind()
        .execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM trips WHERE status = 'CANCELED')")
        )
        .scalar()
        or op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM deliveries WHERE status = 'CANCELED')"
            )
        )
        .scalar()
        or op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM load_plans WHERE status = 'CANCELED')"
            )
        )
        .scalar()
    ):
        raise RuntimeError("OC94 cancellation history exists: downgrade refused")

    op.drop_table("trip_cancellations")
    op.drop_constraint(
        "ck_load_plans__approval_consistent", "load_plans", type_="check"
    )
    op.drop_constraint(
        "ck_load_plans__status_metrics_consistent", "load_plans", type_="check"
    )
    op.drop_constraint("ck_load_plans__status_allowed", "load_plans", type_="check")
    op.create_check_constraint(
        "ck_load_plans__status_allowed",
        "load_plans",
        "status IN ('CALCULATED', 'APPROVED', 'REJECTED')",
    )
    op.create_check_constraint(
        "ck_load_plans__status_metrics_consistent",
        "load_plans",
        "(status = 'REJECTED' AND loaded_count = 0 AND unloaded_count > 0 "
        "AND used_volume_cm3 = 0 AND total_weight_kg = 0 "
        "AND occupancy_percent = 0) OR "
        "(status IN ('CALCULATED', 'APPROVED') AND loaded_count > 0 "
        "AND used_volume_cm3 > 0 AND total_weight_kg > 0)",
    )
    op.create_check_constraint(
        "ck_load_plans__approval_consistent",
        "load_plans",
        "(status = 'APPROVED' AND approved_at IS NOT NULL AND unloaded_count = 0) "
        "OR (status <> 'APPROVED' AND approved_at IS NULL)",
    )
    op.drop_index("uq_deliveries__part_order", table_name="deliveries")
    op.drop_index("uq_deliveries__legacy_order", table_name="deliveries")
    op.create_unique_constraint(
        "uq_deliveries__part_order",
        "deliveries",
        ["distribution_part_id", "order_id"],
    )
    op.create_index(
        "uq_deliveries__legacy_order",
        "deliveries",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("distribution_part_id IS NULL"),
    )
    op.drop_constraint("ck_deliveries__status_allowed", "deliveries", type_="check")
    op.create_check_constraint(
        "ck_deliveries__status_allowed",
        "deliveries",
        "status IN ('PENDING', 'IN_DELIVERY', 'DELIVERED')",
    )
    op.drop_constraint("ck_trips__timestamps_consistent", "trips", type_="check")
    op.drop_constraint("ck_trips__status_allowed", "trips", type_="check")
    op.create_check_constraint(
        "ck_trips__status_allowed",
        "trips",
        "status IN ('SCHEDULED', 'IN_ROUTE', 'FINISHED')",
    )
    op.create_check_constraint(
        "ck_trips__timestamps_consistent",
        "trips",
        "(status = 'SCHEDULED' AND started_at IS NULL AND finished_at IS NULL) "
        "OR (status = 'IN_ROUTE' AND started_at IS NOT NULL "
        "AND finished_at IS NULL) OR "
        "(status = 'FINISHED' AND started_at IS NOT NULL "
        "AND finished_at IS NOT NULL AND finished_at >= started_at)",
    )
