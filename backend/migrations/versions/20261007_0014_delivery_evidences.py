"""delivery evidence contract

Revision ID: 20261007_0014
Revises: 20261006_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261007_0014"
down_revision: str | None = "20261006_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_evidences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), nullable=False),
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["delivery_id"], ["deliveries.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"], ["status_history.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_delivery_evidences__recorded_by_users",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_delivery_evidences__revoked_by_users",
        ),
        sa.UniqueConstraint("recorded_by", "event_id"),
        sa.CheckConstraint("kind IN ('PHOTO', 'SIGNATURE')", name="kind_allowed"),
        sa.CheckConstraint(
            "media_type IN ('image/png', 'image/jpeg')", name="media_type_allowed"
        ),
        sa.CheckConstraint("size_bytes BETWEEN 1 AND 5242880", name="size_allowed"),
        sa.CheckConstraint(
            "length(sha256) = 64 AND length(fingerprint) = 64", name="hash_lengths"
        ),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND revoked_at IS NULL AND revoked_by IS NULL) OR "
            "(status = 'REVOKED' AND revoked_at IS NOT NULL AND revoked_by IS NOT NULL)",
            name="revocation_consistent",
        ),
    )
    op.create_index(
        "ix_delivery_evidences__delivery_recorded",
        "delivery_evidences",
        ["delivery_id", "recorded_at", "id"],
    )


def downgrade() -> None:
    op.drop_table("delivery_evidences")
