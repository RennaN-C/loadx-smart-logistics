"""create auth login throttles

Revision ID: 20260808_0005
Revises: 20260804_0004
Create Date: 2026-08-08 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0005"
down_revision: str | None = "20260804_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_login_throttles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("subject_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "failed_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "failed_count >= 0",
            name=op.f("ck_auth_login_throttles__failed_count_non_negative"),
        ),
        sa.CheckConstraint(
            "scope IN ('ACCOUNT', 'IP')",
            name=op.f("ck_auth_login_throttles__scope_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_login_throttles")),
        sa.UniqueConstraint(
            "scope",
            "subject_hash",
            name="uq_auth_login_throttles__scope_subject_hash",
        ),
    )
    op.create_index(
        op.f("ix_auth_login_throttles__blocked_until"),
        "auth_login_throttles",
        ["blocked_until"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_auth_login_throttles__blocked_until"),
        table_name="auth_login_throttles",
    )
    op.drop_table("auth_login_throttles")
