"""Add lifecycle flags and registry audit catalog (OC105)."""

import sqlalchemy as sa
from alembic import op

revision = "20261008_0016"
down_revision = "20261007_0015"
branch_labels = None
depends_on = None


def _audit_constraints(events: str, entities: str) -> None:
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
    for table in ("customers", "products"):
        op.add_column(
            table,
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    _audit_constraints(
        "'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED'",
        "'USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER'",
    )


def downgrade() -> None:
    # Restore the previous audit catalog without removing operational history.
    op.execute(
        "DELETE FROM audit_events WHERE event_type IN ('RECORD_ARCHIVED', 'RECORD_REACTIVATED') OR entity_type IN ('CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER')"
    )
    _audit_constraints("'USER_CREATED', 'USER_UPDATED'", "'USER'")
    for table in ("products", "customers"):
        op.drop_column(table, "active")
