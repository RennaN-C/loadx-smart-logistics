"""link users to drivers

Revision ID: 20260809_0007
Revises: 20260808_0006
Create Date: 2026-08-09 15:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0007"
down_revision: str | None = "20260808_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("driver_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_users__drivers"),
        "users",
        "drivers",
        ["driver_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        op.f("uq_users__driver_id"),
        "users",
        ["driver_id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_users__driver_id"), "users", type_="unique")
    op.drop_constraint(op.f("fk_users__drivers"), "users", type_="foreignkey")
    op.drop_column("users", "driver_id")
