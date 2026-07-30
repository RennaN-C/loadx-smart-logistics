"""create order tables

Revision ID: 20260730_0002
Revises: 20260729_0001
Create Date: 2026-07-30 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0002"
down_revision: str | None = "20260729_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("delivery_address", sa.String(length=255), nullable=False),
        sa.Column("expected_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'READY', 'PLANNED', 'IN_TRANSIT', 'DELIVERED', 'CANCELED')",
            name=op.f("ck_orders__status_allowed"),
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_orders__customers"),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
    )
    op.create_index("ix_orders__customer_id", "orders", ["customer_id"], unique=False)
    op.create_index("ix_orders__expected_delivery_at", "orders", ["expected_delivery_at"], unique=False)
    op.create_index("ix_orders__status", "orders", ["status"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("delivery_sequence", sa.Integer(), nullable=False),
        sa.CheckConstraint("delivery_sequence > 0", name=op.f("ck_order_items__delivery_sequence_positive")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_order_items__quantity_positive")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name="fk_order_items__orders"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_order_items__products"),
        sa.PrimaryKeyConstraint("id", name="pk_order_items"),
    )
    op.create_index("ix_order_items__order_id", "order_items", ["order_id"], unique=False)
    op.create_index("ix_order_items__product_id", "order_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_order_items__product_id", table_name="order_items")
    op.drop_index("ix_order_items__order_id", table_name="order_items")
    op.drop_table("order_items")

    op.drop_index("ix_orders__status", table_name="orders")
    op.drop_index("ix_orders__expected_delivery_at", table_name="orders")
    op.drop_index("ix_orders__customer_id", table_name="orders")
    op.drop_table("orders")
