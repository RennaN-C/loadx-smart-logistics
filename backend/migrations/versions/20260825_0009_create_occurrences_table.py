"""create occurrences table

Revision ID: 20260825_0009
Revises: 20260809_0008
Create Date: 2026-08-25 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0009"
down_revision: str | None = "20260809_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "occurrences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("photo_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["deliveries.id"],
            name=op.f("fk_occurrences__deliveries"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"],
            ["trips.id"],
            name=op.f("fk_occurrences__trips"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_occurrences")),
    )
    op.create_index(op.f("ix_occurrences__trip_id"), "occurrences", ["trip_id"])
    op.create_index(op.f("ix_occurrences__delivery_id"), "occurrences", ["delivery_id"])
    op.create_index(op.f("ix_occurrences__type"), "occurrences", ["type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_occurrences__type"), table_name="occurrences")
    op.drop_index(op.f("ix_occurrences__delivery_id"), table_name="occurrences")
    op.drop_index(op.f("ix_occurrences__trip_id"), table_name="occurrences")
    op.drop_table("occurrences")
