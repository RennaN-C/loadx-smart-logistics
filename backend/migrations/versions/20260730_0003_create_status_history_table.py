"""create status history table

Revision ID: 20260730_0003
Revises: 20260730_0002
Create Date: 2026-07-30 01:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0003"
down_revision: str | None = "20260730_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("old_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"], ["users.id"], name="fk_status_history__users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_status_history"),
    )
    op.create_index(
        "ix_status_history__created_at", "status_history", ["created_at"], unique=False
    )
    op.create_index(
        "ix_status_history__entity",
        "status_history",
        ["entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_status_history__entity", table_name="status_history")
    op.drop_index("ix_status_history__created_at", table_name="status_history")
    op.drop_table("status_history")
