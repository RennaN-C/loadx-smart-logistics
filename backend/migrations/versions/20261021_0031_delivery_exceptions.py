"""oc94 delivery exception attempts.

Revision ID: 20261021_0031
Revises: 20261021_0030
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_0031"
down_revision: str | None = "20261021_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_exceptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "code IN ('CUSTOMER_ABSENT', 'REFUSED', 'DAMAGED', "
            "'OPERATIONAL_FAILURE', 'RESCHEDULED', 'RESUMED')",
            name=op.f("ck_delivery_exceptions__code_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["deliveries.id"],
            name=op.f("fk_delivery_exceptions__deliveries"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"],
            ["trips.id"],
            name=op.f("fk_delivery_exceptions__trips"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_delivery_exceptions__users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delivery_exceptions")),
        sa.UniqueConstraint(
            "delivery_id",
            "idempotency_key",
            name="uq_delivery_exceptions__delivery_request",
        ),
    )
    op.create_index(
        "ix_delivery_exceptions__delivery_created",
        "delivery_exceptions",
        ["delivery_id", "created_at"],
    )


def downgrade() -> None:
    if op.get_bind().execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM delivery_exceptions)")
    ).scalar():
        raise RuntimeError("OC94 records exist: downgrade would destroy history")
    op.drop_index(
        "ix_delivery_exceptions__delivery_created", table_name="delivery_exceptions"
    )
    op.drop_table("delivery_exceptions")
