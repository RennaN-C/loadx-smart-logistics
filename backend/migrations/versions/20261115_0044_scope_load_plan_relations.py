"""G05-B: scope plan order links and volume provenance by organization.

The plan header was scoped in 0043; this revision enforces the same owner
for linked orders, order items, and products. Multi-tenant operational access
remains disabled until the remaining domains are isolated.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0044"
down_revision = "20261115_0043"
branch_labels = None
depends_on = None

LEGACY = "00000000-0000-4000-8000-000000000301"
LEGACY_DEFAULT = sa.text("'00000000-0000-4000-8000-000000000301'")


def upgrade() -> None:
    # Reject inconsistent historic ownership, rather than mislabeling it.
    # Use a server-side guard so alembic upgrade head --sql works as well.
    op.execute(
        sa.text(
            f"""
            DO $loadx_g05b$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM load_plan_orders AS link
                    JOIN load_plans AS plan ON plan.id = link.load_plan_id
                    JOIN orders AS ord ON ord.id = link.order_id
                    WHERE plan.organization_id <> CAST('{LEGACY}' AS uuid)
                       OR ord.organization_id <> plan.organization_id
                ) OR EXISTS (
                    SELECT 1 FROM load_plan_items AS volume
                    JOIN load_plans AS plan ON plan.id = volume.load_plan_id
                    JOIN orders AS ord ON ord.id = volume.order_id
                    JOIN order_items AS item ON item.id = volume.order_item_id
                    JOIN products AS product ON product.id = volume.product_id
                    WHERE plan.organization_id <> CAST('{LEGACY}' AS uuid)
                       OR ord.organization_id <> plan.organization_id
                       OR item.organization_id <> plan.organization_id
                       OR product.organization_id <> plan.organization_id
                ) THEN
                    RAISE EXCEPTION 'G05-B upgrade refused: planning children reference a non-legacy or cross-organization resource.';
                END IF;
            END
            $loadx_g05b$;
            """
        )
    )

    op.add_column(
        "load_plan_orders",
        sa.Column(
            "organization_id", sa.Uuid(), nullable=False, server_default=LEGACY_DEFAULT
        ),
    )
    op.create_unique_constraint(
        "uq_load_plan_orders__org_plan_order",
        "load_plan_orders",
        ["organization_id", "load_plan_id", "order_id"],
    )
    op.create_foreign_key(
        "fk_load_plan_orders__organization_plan",
        "load_plan_orders",
        "load_plans",
        ["organization_id", "load_plan_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_load_plan_orders__organization_order",
        "load_plan_orders",
        "orders",
        ["organization_id", "order_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "load_plan_items",
        sa.Column(
            "organization_id", sa.Uuid(), nullable=False, server_default=LEGACY_DEFAULT
        ),
    )
    op.create_foreign_key(
        "fk_load_plan_items__organization_plan_order",
        "load_plan_items",
        "load_plan_orders",
        ["organization_id", "load_plan_id", "order_id"],
        ["organization_id", "load_plan_id", "order_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_load_plan_items__organization_order_item",
        "load_plan_items",
        "order_items",
        ["organization_id", "order_item_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_load_plan_items__organization_product",
        "load_plan_items",
        "products",
        ["organization_id", "product_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DO $loadx_g05b$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM load_plan_orders
                    WHERE organization_id <> CAST('{LEGACY}' AS uuid)
                ) OR EXISTS (
                    SELECT 1 FROM load_plan_items
                    WHERE organization_id <> CAST('{LEGACY}' AS uuid)
                ) THEN
                    RAISE EXCEPTION 'G05-B downgrade refused: non-legacy plan children cannot be collapsed.';
                END IF;
            END
            $loadx_g05b$;
            """
        )
    )

    for name in (
        "fk_load_plan_items__organization_product",
        "fk_load_plan_items__organization_order_item",
        "fk_load_plan_items__organization_plan_order",
    ):
        op.drop_constraint(name, "load_plan_items", type_="foreignkey")
    op.drop_column("load_plan_items", "organization_id")

    for name in (
        "fk_load_plan_orders__organization_order",
        "fk_load_plan_orders__organization_plan",
    ):
        op.drop_constraint(name, "load_plan_orders", type_="foreignkey")
    op.drop_constraint(
        "uq_load_plan_orders__org_plan_order",
        "load_plan_orders",
        type_="unique",
    )
    op.drop_column("load_plan_orders", "organization_id")
