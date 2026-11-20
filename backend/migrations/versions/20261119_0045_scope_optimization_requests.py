"""G05-C: organization-scoped optimization recovery identities.

Distribution ownership is proven through its already scoped parents. The
composite distribution FK is intentionally deferred to G06.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261119_0045"
down_revision = "20261115_0044"
branch_labels = None
depends_on = None

LEGACY = "00000000-0000-4000-8000-000000000301"


def upgrade() -> None:
    # Serialize the ownership preflight with modifications to its evidence.
    op.execute(
        sa.text(
            "LOCK TABLE optimization_requests, load_distributions, "
            "load_distribution_orders, load_distribution_parts, load_distribution_volumes, "
            "orders, order_items, products, load_plans, organization_memberships "
            "IN SHARE ROW EXCLUSIVE MODE"
        )
    )
    op.execute(
        sa.text(f"""
        DO $loadx_g05c$
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
                SELECT 1 FROM optimization_requests AS request
                WHERE NOT EXISTS (
                    SELECT 1 FROM owners
                    WHERE owners.distribution_id = request.distribution_id
                ) OR EXISTS (
                    SELECT 1 FROM owners
                    WHERE owners.distribution_id = request.distribution_id
                      AND owners.organization_id <> CAST('{LEGACY}' AS uuid)
                ) OR NOT EXISTS (
                    SELECT 1 FROM organization_memberships AS membership
                    WHERE membership.organization_id = CAST('{LEGACY}' AS uuid)
                      AND membership.user_id = request.user_id
                )
            ) THEN
                RAISE EXCEPTION 'G05-C upgrade refused: missing ownership, non-legacy or cross-organization parents, or missing actor membership.';
            END IF;
        END
        $loadx_g05c$;
    """)
    )
    # A checked constant backfill avoids UPDATE plus pending RI trigger events.
    # The temporary default is removed: all subsequent writers supply context.
    op.add_column(
        "optimization_requests",
        sa.Column(
            "organization_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text(f"'{LEGACY}'"),
        ),
    )
    op.alter_column("optimization_requests", "organization_id", server_default=None)
    op.drop_constraint(
        "pk_optimization_requests", "optimization_requests", type_="primary"
    )
    op.create_primary_key(
        "pk_optimization_requests",
        "optimization_requests",
        ["organization_id", "user_id", "request_key"],
    )
    op.create_foreign_key(
        "fk_optimization_requests__organizations",
        "optimization_requests",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_optimization_requests__organization_user",
        "optimization_requests",
        "organization_memberships",
        ["organization_id", "user_id"],
        ["organization_id", "user_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.execute(sa.text("LOCK TABLE optimization_requests IN ACCESS EXCLUSIVE MODE"))
    op.execute(
        sa.text(f"""
        DO $loadx_g05c$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM optimization_requests
                WHERE organization_id <> CAST('{LEGACY}' AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM optimization_requests
                GROUP BY user_id, request_key HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'G05-C downgrade refused: non-legacy requests or colliding legacy identities cannot be collapsed.';
            END IF;
        END
        $loadx_g05c$;
    """)
    )
    op.drop_constraint(
        "fk_optimization_requests__organization_user",
        "optimization_requests",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_optimization_requests__organizations",
        "optimization_requests",
        type_="foreignkey",
    )
    op.drop_constraint(
        "pk_optimization_requests", "optimization_requests", type_="primary"
    )
    op.create_primary_key(
        "pk_optimization_requests", "optimization_requests", ["user_id", "request_key"]
    )
    op.drop_column("optimization_requests", "organization_id")
