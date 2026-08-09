"""create auth sessions

Revision ID: 20260808_0006
Revises: 20260808_0005
Create Date: 2026-08-08 00:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0006"
down_revision: str | None = "20260808_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "absolute_expires_at > created_at",
            name=op.f("ck_auth_sessions__absolute_expiration_after_creation"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_auth_sessions__users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint(
            "token_hash",
            name=op.f("uq_auth_sessions__token_hash"),
        ),
    )
    op.create_index(
        op.f("ix_auth_sessions__idle_expires_at"),
        "auth_sessions",
        ["idle_expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_auth_sessions__user_id"),
        "auth_sessions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_sessions__user_id"), table_name="auth_sessions")
    op.drop_index(
        op.f("ix_auth_sessions__idle_expires_at"),
        table_name="auth_sessions",
    )
    op.drop_table("auth_sessions")
