"""external command idempotency

Revision ID: 20261006_0012
Revises: 20260830_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261006_0012"
down_revision: str | None = "20260830_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_commands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("command", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_external_commands"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_external_commands__users"
        ),
        sa.UniqueConstraint(
            "integration_id",
            "event_hash",
            name="uq_external_commands__integration_id_event_hash",
        ),
        sa.CheckConstraint(
            "event_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_external_commands__event_hash_valid"),
        ),
        sa.CheckConstraint(
            "fingerprint ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_external_commands__fingerprint_valid"),
        ),
        sa.CheckConstraint(
            "command IN ('START_TRIP', 'START_DELIVERY', 'FINISH_DELIVERY')",
            name=op.f("ck_external_commands__command_allowed"),
        ),
    )


def downgrade() -> None:
    op.drop_table("external_commands")
