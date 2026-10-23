"""Committed idempotent optimization results, without changing existing distributions."""

import sqlalchemy as sa
from alembic import op

revision = "20261023_0035"
down_revision = "20261021_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimization_requests",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("request_key", sa.Uuid(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("distribution_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "request_key"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["distribution_id"], ["load_distributions.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("distribution_id"),
        sa.CheckConstraint("length(payload_hash) = 64", name="payload_hash_length"),
    )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(sa.text("SELECT EXISTS (SELECT 1 FROM optimization_requests)"))
        .scalar()
    ):
        raise RuntimeError(
            "Downgrade blocked: preserve optimization request identities."
        )
    op.drop_table("optimization_requests")
