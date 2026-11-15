"""G04: scope orders and order_items to their customer organization.

Order ownership is backfilled from the customer, item ownership from the
parent order. The second organization stays operationally disabled until
planning, trips, deliveries, outbox, and all other domains are isolated.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0042"
down_revision = "20261115_0041"
branch_labels = None
depends_on = None

LEGACY = "00000000-0000-4000-8000-000000000301"
LEGACY_DEFAULT = sa.text("'00000000-0000-4000-8000-000000000301'")


def upgrade() -> None:
    op.add_column("orders", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE orders AS child
        SET organization_id = owner.organization_id
        FROM customers AS owner
        WHERE child.customer_id = owner.id
        """
    )
    # Any orphan or inconsistent source fails before a constraint is relaxed.
    op.alter_column("orders", "organization_id", nullable=False)
    op.alter_column("orders", "organization_id", server_default=LEGACY_DEFAULT)
    op.create_foreign_key(
        "fk_orders__organizations",
        "orders",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_orders__organization_id", "orders", ["organization_id", "id"]
    )
    op.drop_constraint("fk_orders__customers", "orders", type_="foreignkey")
    op.create_foreign_key(
        "fk_orders__organization_customer",
        "orders",
        "customers",
        ["organization_id", "customer_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    # Preserve the historical address/customer pairing FK. This *additional*
    # constraint guarantees the selected address is also in the same tenant.
    op.create_foreign_key(
        "fk_orders__organization_customer_address",
        "orders",
        "customer_addresses",
        ["organization_id", "customer_address_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "order_items", sa.Column("organization_id", sa.Uuid(), nullable=True)
    )
    op.execute(
        """
        UPDATE order_items AS child
        SET organization_id = owner.organization_id
        FROM orders AS owner
        WHERE child.order_id = owner.id
        """
    )
    op.alter_column("order_items", "organization_id", nullable=False)
    op.alter_column(
        "order_items", "organization_id", server_default=LEGACY_DEFAULT
    )
    op.create_unique_constraint(
        "uq_order_items__organization_id",
        "order_items",
        ["organization_id", "id"],
    )
    op.drop_constraint(
        "fk_order_items__orders", "order_items", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_order_items__products", "order_items", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_order_items__organization_order",
        "order_items",
        "orders",
        ["organization_id", "order_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_order_items__organization_product",
        "order_items",
        "products",
        ["organization_id", "product_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM orders
                WHERE organization_id <> CAST(:legacy AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM order_items
                WHERE organization_id <> CAST(:legacy AS uuid)
            )
            """
        ),
        {"legacy": LEGACY},
    ).scalar():
        raise RuntimeError(
            "G04 downgrade refused: orders from non-legacy organizations "
            "cannot be collapsed into the global catalog."
        )

    op.drop_constraint(
        "fk_order_items__organization_product",
        "order_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_order_items__organization_order",
        "order_items",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_order_items__products",
        "order_items",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_order_items__orders",
        "order_items",
        "orders",
        ["order_id"],
        ["id"],
    )
    op.drop_constraint(
        "uq_order_items__organization_id", "order_items", type_="unique"
    )
    op.drop_column("order_items", "organization_id")

    op.drop_constraint(
        "fk_orders__organization_customer_address",
        "orders",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_orders__organization_customer", "orders", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_orders__customers",
        "orders",
        "customers",
        ["customer_id"],
        ["id"],
    )
    op.drop_constraint("uq_orders__organization_id", "orders", type_="unique")
    op.drop_constraint(
        "fk_orders__organizations", "orders", type_="foreignkey"
    )
    op.drop_column("orders", "organization_id")
