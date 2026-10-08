"""Reusable customer addresses and immutable order snapshots (OC99)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261008_0017"
down_revision = "20261008_0016"
branch_labels = None
depends_on = None

ADDRESS_EVENTS = "'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED'"
PREVIOUS_EVENTS = (
    "'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED'"
)
PREVIOUS_ENTITIES = "'USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER'"


def _audit_catalog(events: str, entities: str) -> None:
    for name in ("event_type_allowed", "entity_type_allowed"):
        op.drop_constraint(
            op.f(f"ck_audit_events__{name}"), "audit_events", type_="check"
        )
    op.create_check_constraint(
        op.f("ck_audit_events__event_type_allowed"),
        "audit_events",
        f"event_type IN ({events})",
    )
    op.create_check_constraint(
        op.f("ck_audit_events__entity_type_allowed"),
        "audit_events",
        f"entity_type IN ({entities})",
    )


def upgrade() -> None:
    op.create_table(
        "customer_addresses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "customer_id",
            sa.Uuid(),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("postal_code", sa.String(8)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "id", "customer_id", name="uq_customer_addresses__id_customer"
        ),
        sa.CheckConstraint("NOT is_primary OR active", name="primary_active"),
    )
    op.create_index(
        "ix_customer_addresses__customer_id", "customer_addresses", ["customer_id"]
    )
    op.create_index(
        "uq_customer_addresses__primary",
        "customer_addresses",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    op.execute("""
        INSERT INTO customer_addresses (id, customer_id, label, address, city, state, active, is_primary, created_at)
        SELECT md5(id::text || '-legacy-address')::uuid, id, 'Principal', address, city, state, true, true, created_at FROM customers
    """)
    op.add_column("orders", sa.Column("customer_address_id", sa.Uuid()))
    op.add_column("orders", sa.Column("delivery_address_snapshot", postgresql.JSONB()))
    op.create_index("ix_orders__customer_address_id", "orders", ["customer_address_id"])
    op.create_foreign_key(
        "fk_orders__customer_addresses",
        "orders",
        "customer_addresses",
        ["customer_address_id", "customer_id"],
        ["id", "customer_id"],
        ondelete="RESTRICT",
    )
    op.execute(
        "UPDATE orders SET delivery_address_snapshot = jsonb_build_object('address', delivery_address)"
    )
    _audit_catalog(
        f"{PREVIOUS_EVENTS}, {ADDRESS_EVENTS}",
        f"{PREVIOUS_ENTITIES}, 'CUSTOMER_ADDRESS'",
    )


DOWNGRADE_GUARD_QUERY = sa.text("""
    SELECT EXISTS (
        SELECT 1 FROM customer_addresses a JOIN customers c ON c.id = a.customer_id
        WHERE a.id <> md5(c.id::text || '-legacy-address')::uuid
           OR NOT a.active OR NOT a.is_primary OR a.label <> 'Principal'
           OR a.postal_code IS NOT NULL
           OR (a.address, a.city, a.state) IS DISTINCT FROM (c.address, c.city, c.state)
    ) OR EXISTS (
        SELECT 1 FROM orders WHERE customer_address_id IS NOT NULL
        OR (delivery_address_snapshot IS NOT NULL AND delivery_address_snapshot <> jsonb_build_object('address', delivery_address))
    ) OR EXISTS (SELECT 1 FROM audit_events WHERE entity_type = 'CUSTOMER_ADDRESS')
""")


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(DOWNGRADE_GUARD_QUERY):
        raise RuntimeError(
            "OC99 downgrade blocked: reusable addresses, order provenance or address audit must be preserved"
        )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE customers, customer_addresses, orders, audit_events IN SHARE ROW EXCLUSIVE MODE"
    )
    ensure_safe_downgrade(op.get_bind())
    _audit_catalog(PREVIOUS_EVENTS, PREVIOUS_ENTITIES)
    op.drop_constraint("fk_orders__customer_addresses", "orders", type_="foreignkey")
    op.drop_index("ix_orders__customer_address_id", table_name="orders")
    op.drop_column("orders", "delivery_address_snapshot")
    op.drop_column("orders", "customer_address_id")
    op.drop_table("customer_addresses")
