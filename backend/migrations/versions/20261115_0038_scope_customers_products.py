"""G02: scope customer, address and product registries by organization.

Only the legacy organization can authenticate operationally at this stage.
Organization switching and other operational modules remain disabled.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0038"
down_revision = "20261115_0037"
branch_labels = None
depends_on = None

LEGACY_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000301"
LEGACY_DEFAULT = sa.text("'00000000-0000-4000-8000-000000000301'")


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "organization_id", sa.Uuid(), nullable=False, server_default=LEGACY_DEFAULT
        ),
    )
    op.create_foreign_key(
        op.f("fk_customers__organizations"),
        "customers",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(op.f("uq_customers__document"), "customers", type_="unique")
    op.create_unique_constraint(
        op.f("uq_customers__organization_document"),
        "customers",
        ["organization_id", "document"],
    )
    op.create_unique_constraint(
        op.f("uq_customers__organization_id"), "customers", ["organization_id", "id"]
    )

    op.add_column(
        "products",
        sa.Column(
            "organization_id", sa.Uuid(), nullable=False, server_default=LEGACY_DEFAULT
        ),
    )
    op.create_foreign_key(
        op.f("fk_products__organizations"),
        "products",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(op.f("uq_products__code"), "products", type_="unique")
    op.create_unique_constraint(
        op.f("uq_products__organization_code"),
        "products",
        ["organization_id", "code"],
    )
    op.create_unique_constraint(
        op.f("uq_products__organization_id"), "products", ["organization_id", "id"]
    )

    # Backfill addresses from their actual parent; do not infer tenant from
    # users or the actor that created a record.
    op.add_column(
        "customer_addresses",
        sa.Column("organization_id", sa.Uuid(), nullable=True),
    )
    op.execute(
        """
        UPDATE customer_addresses AS a
        SET organization_id = c.organization_id
        FROM customers AS c
        WHERE a.customer_id = c.id
        """
    )
    op.alter_column("customer_addresses", "organization_id", nullable=False)
    op.alter_column(
        "customer_addresses",
        "organization_id",
        server_default=LEGACY_DEFAULT,
    )
    op.create_unique_constraint(
        op.f("uq_customer_addresses__organization_id"),
        "customer_addresses",
        ["organization_id", "id"],
    )
    op.drop_constraint(
        op.f("fk_customer_addresses__customers"),
        "customer_addresses",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_customer_addresses__organization_customer",
        "customer_addresses",
        "customers",
        ["organization_id", "customer_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.drop_index("uq_customer_addresses__primary", table_name="customer_addresses")
    op.create_index(
        "uq_customer_addresses__primary",
        "customer_addresses",
        ["organization_id", "customer_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM customers
                WHERE organization_id <> CAST(:legacy_id AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM customer_addresses
                WHERE organization_id <> CAST(:legacy_id AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM products
                WHERE organization_id <> CAST(:legacy_id AS uuid)
            )
            """
        ),
        {"legacy_id": LEGACY_ORGANIZATION_ID},
    ).scalar():
        raise RuntimeError(
            "G02 downgrade refused: non-legacy customers, addresses or products "
            "cannot be collapsed into global registries."
        )

    op.drop_index("uq_customer_addresses__primary", table_name="customer_addresses")
    op.create_index(
        "uq_customer_addresses__primary",
        "customer_addresses",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    op.drop_constraint(
        "fk_customer_addresses__organization_customer",
        "customer_addresses",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_customer_addresses__customers"),
        "customer_addresses",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        op.f("uq_customer_addresses__organization_id"),
        "customer_addresses",
        type_="unique",
    )
    op.drop_column("customer_addresses", "organization_id")

    op.drop_constraint(
        op.f("uq_products__organization_code"), "products", type_="unique"
    )
    op.drop_constraint(op.f("uq_products__organization_id"), "products", type_="unique")
    op.create_unique_constraint(op.f("uq_products__code"), "products", ["code"])
    op.drop_constraint(
        op.f("fk_products__organizations"), "products", type_="foreignkey"
    )
    op.drop_column("products", "organization_id")

    op.drop_constraint(
        op.f("uq_customers__organization_document"),
        "customers",
        type_="unique",
    )
    op.drop_constraint(
        op.f("uq_customers__organization_id"), "customers", type_="unique"
    )
    op.create_unique_constraint(
        op.f("uq_customers__document"), "customers", ["document"]
    )
    op.drop_constraint(
        op.f("fk_customers__organizations"), "customers", type_="foreignkey"
    )
    op.drop_column("customers", "organization_id")
