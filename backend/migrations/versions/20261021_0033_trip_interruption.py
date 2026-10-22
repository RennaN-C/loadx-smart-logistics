"""OC94: auditable trip interruption and resumption without unloading cargo.

Revision ID: 20261021_0033
Revises: 20261021_0032
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_0033"
down_revision: str | None = "20261021_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_trips__status_allowed"), "trips", type_="check")
    op.drop_constraint(op.f("ck_trips__timestamps_consistent"), "trips", type_="check")
    op.create_check_constraint(
        op.f("ck_trips__status_allowed"),
        "trips",
        "status IN ('SCHEDULED','IN_ROUTE','INTERRUPTED','FINISHED','CANCELED')",
    )
    op.create_check_constraint(
        op.f("ck_trips__timestamps_consistent"),
        "trips",
        "(status IN ('SCHEDULED','CANCELED') AND started_at IS NULL "
        "AND finished_at IS NULL) OR "
        "(status IN ('IN_ROUTE','INTERRUPTED') AND started_at IS NOT NULL "
        "AND finished_at IS NULL) OR "
        "(status = 'FINISHED' AND started_at IS NOT NULL "
        "AND finished_at IS NOT NULL AND finished_at >= started_at)",
    )
    op.create_table(
        "trip_interruption_events",
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
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "action IN ('INTERRUPTED','RESUMED')",
            name=op.f("ck_trip_interruption_events__action_allowed"),
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name=op.f("uq_trip_interruption_events__request"),
        ),
    )
    op.create_index(
        "ix_trip_interruption_events__trip_id_created_at",
        "trip_interruption_events",
        ["trip_id", "created_at"],
    )


def downgrade() -> None:
    db = op.get_bind()
    if db.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM trip_interruption_events) "
            "OR EXISTS (SELECT 1 FROM trips WHERE status = 'INTERRUPTED')"
        )
    ).scalar():
        raise RuntimeError("OC94 interruption history exists: downgrade refused")
    op.drop_index(
        "ix_trip_interruption_events__trip_id_created_at",
        table_name="trip_interruption_events",
    )
    op.drop_table("trip_interruption_events")
    op.drop_constraint(op.f("ck_trips__timestamps_consistent"), "trips", type_="check")
    op.drop_constraint(op.f("ck_trips__status_allowed"), "trips", type_="check")
    op.create_check_constraint(
        op.f("ck_trips__status_allowed"),
        "trips",
        "status IN ('SCHEDULED', 'IN_ROUTE', 'FINISHED', 'CANCELED')",
    )
    op.create_check_constraint(
        op.f("ck_trips__timestamps_consistent"),
        "trips",
        "(status IN ('SCHEDULED', 'CANCELED') AND started_at IS NULL "
        "AND finished_at IS NULL) OR "
        "(status = 'IN_ROUTE' AND started_at IS NOT NULL "
        "AND finished_at IS NULL) OR "
        "(status = 'FINISHED' AND started_at IS NOT NULL "
        "AND finished_at IS NOT NULL AND finished_at >= started_at)",
    )
