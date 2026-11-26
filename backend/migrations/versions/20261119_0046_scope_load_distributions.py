"""G06-A: scope distribution aggregates and complete optimization result ownership.

No historical row or operational trigger is rewritten. The verified legacy
ownership permits a temporary constant default, removed before new writes.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261119_0046"
down_revision = "20261119_0045"
branch_labels = None
depends_on = None

LEGACY = "00000000-0000-4000-8000-000000000301"
TABLES = (
    "load_distributions",
    "load_distribution_orders",
    "load_distribution_parts",
    "load_distribution_volumes",
)


def _lock_sources() -> None:
    op.execute(
        sa.text(
            "LOCK TABLE optimization_requests, load_distributions, "
            "load_distribution_orders, load_distribution_parts, load_distribution_volumes, "
            "orders, order_items, products, load_plans, organization_memberships "
            "IN SHARE ROW EXCLUSIVE MODE"
        )
    )


def _foreign_key(name, source, target, columns, referred_columns) -> None:
    op.create_foreign_key(
        name, source, target, columns, referred_columns, ondelete="RESTRICT"
    )


def _claim_indexes(*, scoped: bool) -> None:
    prefix = ["organization_id"] if scoped else []
    op.drop_index(
        "uq_load_distribution_orders__active_order",
        table_name="load_distribution_orders",
    )
    op.create_index(
        "uq_load_distribution_orders__active_order",
        "load_distribution_orders",
        [*prefix, "order_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.drop_index(
        "uq_load_distribution_volumes__active_identity",
        table_name="load_distribution_volumes",
    )
    op.create_index(
        "uq_load_distribution_volumes__active_identity",
        "load_distribution_volumes",
        [*prefix, "order_item_id", "volume_index"],
        unique=True,
        postgresql_where=sa.text("active"),
    )


def upgrade() -> None:
    _lock_sources()
    op.execute(
        sa.text(f"""
        DO $loadx_g06a$
        BEGIN
            IF EXISTS (
                WITH owners AS (
                    SELECT link.distribution_id, ord.organization_id
                    FROM load_distribution_orders AS link
                    JOIN orders AS ord ON ord.id = link.order_id
                    UNION ALL
                    SELECT part.distribution_id, plan.organization_id
                    FROM load_distribution_parts AS part
                    JOIN load_plans AS plan ON plan.id = part.load_plan_id
                    UNION ALL
                    SELECT volume.distribution_id, item.organization_id
                    FROM load_distribution_volumes AS volume
                    JOIN order_items AS item ON item.id = volume.order_item_id
                    UNION ALL
                    SELECT volume.distribution_id, product.organization_id
                    FROM load_distribution_volumes AS volume
                    JOIN products AS product ON product.id = volume.product_id
                )
                SELECT 1 FROM load_distributions AS distribution
                WHERE NOT EXISTS (
                    SELECT 1 FROM owners
                    WHERE owners.distribution_id = distribution.id
                ) OR EXISTS (
                    SELECT 1 FROM owners
                    WHERE owners.distribution_id = distribution.id
                      AND owners.organization_id <> CAST('{LEGACY}' AS uuid)
                ) OR NOT EXISTS (
                    SELECT 1 FROM organization_memberships AS membership
                    WHERE membership.organization_id = CAST('{LEGACY}' AS uuid)
                      AND membership.user_id = distribution.created_by
                )
            ) OR EXISTS (
                SELECT 1 FROM optimization_requests AS request
                LEFT JOIN load_distributions AS distribution
                    ON distribution.id = request.distribution_id
                WHERE request.organization_id <> CAST('{LEGACY}' AS uuid)
                   OR distribution.id IS NULL
            ) THEN
                RAISE EXCEPTION 'G06-A upgrade refused: missing ownership, non-legacy or cross-organization parents, creator membership or optimization result mismatch.';
            END IF;
        END
        $loadx_g06a$;
    """)
    )
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "organization_id",
                sa.Uuid(),
                nullable=False,
                server_default=sa.text(f"'{LEGACY}'"),
            ),
        )
        op.alter_column(table, "organization_id", server_default=None)

    op.create_unique_constraint(
        "uq_load_distributions__organization_id",
        "load_distributions",
        ["organization_id", "id"],
    )
    _foreign_key(
        "fk_load_distributions__organizations",
        "load_distributions",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    _foreign_key(
        "fk_load_distributions__organization_user",
        "load_distributions",
        "organization_memberships",
        ["organization_id", "created_by"],
        ["organization_id", "user_id"],
    )

    op.create_unique_constraint(
        "uq_load_distribution_orders__org_dist_order",
        "load_distribution_orders",
        ["organization_id", "distribution_id", "order_id"],
    )
    _foreign_key(
        "fk_load_distribution_orders__org_distribution",
        "load_distribution_orders",
        "load_distributions",
        ["organization_id", "distribution_id"],
        ["organization_id", "id"],
    )
    _foreign_key(
        "fk_load_distribution_orders__org_order",
        "load_distribution_orders",
        "orders",
        ["organization_id", "order_id"],
        ["organization_id", "id"],
    )

    op.create_unique_constraint(
        "uq_load_distribution_parts__org_id_dist",
        "load_distribution_parts",
        ["organization_id", "id", "distribution_id"],
    )
    _foreign_key(
        "fk_load_distribution_parts__org_distribution",
        "load_distribution_parts",
        "load_distributions",
        ["organization_id", "distribution_id"],
        ["organization_id", "id"],
    )
    _foreign_key(
        "fk_load_distribution_parts__org_plan",
        "load_distribution_parts",
        "load_plans",
        ["organization_id", "load_plan_id"],
        ["organization_id", "id"],
    )

    _foreign_key(
        "fk_load_distribution_volumes__org_dist_order",
        "load_distribution_volumes",
        "load_distribution_orders",
        ["organization_id", "distribution_id", "order_id"],
        ["organization_id", "distribution_id", "order_id"],
    )
    _foreign_key(
        "fk_load_distribution_volumes__org_part",
        "load_distribution_volumes",
        "load_distribution_parts",
        ["organization_id", "part_id", "distribution_id"],
        ["organization_id", "id", "distribution_id"],
    )
    _foreign_key(
        "fk_load_distribution_volumes__org_item",
        "load_distribution_volumes",
        "order_items",
        ["organization_id", "order_item_id"],
        ["organization_id", "id"],
    )
    _foreign_key(
        "fk_load_distribution_volumes__org_product",
        "load_distribution_volumes",
        "products",
        ["organization_id", "product_id"],
        ["organization_id", "id"],
    )
    _foreign_key(
        "fk_optimization_requests__org_distribution",
        "optimization_requests",
        "load_distributions",
        ["organization_id", "distribution_id"],
        ["organization_id", "id"],
    )
    _claim_indexes(scoped=True)


def downgrade() -> None:
    _lock_sources()
    # Retain all records: refusing non-legacy state also preserves the meaning
    # of the old global partial unique indexes when organization is removed.
    guard = " OR ".join(
        f"EXISTS (SELECT 1 FROM {table} "
        f"WHERE organization_id <> CAST('{LEGACY}' AS uuid))"
        for table in (*TABLES, "optimization_requests")
    )
    op.execute(
        sa.text(f"""
        DO $loadx_g06a$
        BEGIN
            IF {guard} THEN
                RAISE EXCEPTION 'G06-A downgrade refused: non-legacy distribution or optimization data cannot be collapsed.';
            END IF;
        END
        $loadx_g06a$;
    """)
    )
    op.drop_constraint(
        "fk_optimization_requests__org_distribution",
        "optimization_requests",
        type_="foreignkey",
    )
    for suffix in ("org_product", "org_item", "org_part", "org_dist_order"):
        op.drop_constraint(
            f"fk_load_distribution_volumes__{suffix}",
            "load_distribution_volumes",
            type_="foreignkey",
        )
    for suffix in ("org_plan", "org_distribution"):
        op.drop_constraint(
            f"fk_load_distribution_parts__{suffix}",
            "load_distribution_parts",
            type_="foreignkey",
        )
    op.drop_constraint(
        "uq_load_distribution_parts__org_id_dist",
        "load_distribution_parts",
        type_="unique",
    )
    for suffix in ("org_order", "org_distribution"):
        op.drop_constraint(
            f"fk_load_distribution_orders__{suffix}",
            "load_distribution_orders",
            type_="foreignkey",
        )
    op.drop_constraint(
        "uq_load_distribution_orders__org_dist_order",
        "load_distribution_orders",
        type_="unique",
    )
    for suffix in ("organization_user", "organizations"):
        op.drop_constraint(
            f"fk_load_distributions__{suffix}", "load_distributions", type_="foreignkey"
        )
    op.drop_constraint(
        "uq_load_distributions__organization_id", "load_distributions", type_="unique"
    )
    _claim_indexes(scoped=False)
    for table in reversed(TABLES):
        op.drop_column(table, "organization_id")
