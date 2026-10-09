"""OC104: atomic registration imports and auditable results."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261009_0022"
down_revision = "20261009_0021"
branch_labels = None
depends_on = None

CONSTRAINTS = {
    "entity_allowed": "entity_type IN ('customers','products','trucks','drivers')",
    "hash_valid": "sha256 ~ '^[0-9a-f]{64}$' AND fingerprint ~ '^[0-9a-f]{64}$'",
    "counts_allowed": "row_count BETWEEN 0 AND 1000 AND created_count BETWEEN 0 AND row_count AND rejected_count BETWEEN 0 AND row_count",
    "result_arrays": "jsonb_typeof(errors) = 'array' AND jsonb_typeof(records) = 'array'",
    "result_consistent": "(status='PROCESSING' AND created_count=0 AND rejected_count=0 AND jsonb_array_length(errors)=0 AND jsonb_array_length(records)=0) OR (status='COMPLETED' AND row_count>0 AND created_count=row_count AND rejected_count=0 AND jsonb_array_length(errors)=0 AND jsonb_array_length(records)=row_count) OR (status='REJECTED' AND created_count=0 AND rejected_count=row_count AND jsonb_array_length(errors)>0 AND jsonb_array_length(records)=0)",
}
PREVIOUS_EVENTS = "'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED', 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED', 'TRUCK_DOCUMENT_CREATED', 'TRUCK_DOCUMENT_RENEWED', 'TRUCK_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_CREATED', 'DRIVER_DOCUMENT_RENEWED', 'DRIVER_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_TYPE_APPROVED', 'ATTACHMENT_REGISTERED', 'ATTACHMENT_REVOKED'"
PREVIOUS_ENTITIES = "'USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS', 'TRUCK_MAINTENANCE', 'TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY', 'DRIVER_DOCUMENT', 'DRIVER_DOCUMENT_POLICY', 'DRIVER_DOCUMENT_TYPE', 'ATTACHMENT'"


def catalog(events: str, entities: str) -> None:
    for field, values in (("event_type", events), ("entity_type", entities)):
        op.drop_constraint(
            op.f(f"ck_audit_events__{field}_allowed"), "audit_events", type_="check"
        )
        op.create_check_constraint(
            op.f(f"ck_audit_events__{field}_allowed"),
            "audit_events",
            f"{field} IN ({values})",
        )


def upgrade() -> None:
    op.create_table(
        "registration_imports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(16), nullable=False),
        sa.Column(
            "recorded_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PROCESSING"),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("records", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.UniqueConstraint("recorded_by", "event_id"),
        *(sa.CheckConstraint(sql, name=name) for name, sql in CONSTRAINTS.items()),
    )
    op.create_index(
        "ix_registration_imports__entity_recorded",
        "registration_imports",
        ["entity_type", "recorded_at", "id"],
    )
    op.create_index(
        "ix_registration_imports__actor", "registration_imports", ["recorded_by"]
    )
    catalog(
        f"{PREVIOUS_EVENTS}, 'IMPORT_COMPLETED', 'IMPORT_REJECTED'",
        f"{PREVIOUS_ENTITIES}, 'REGISTRATION_IMPORT'",
    )


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM registration_imports) OR EXISTS(SELECT 1 FROM audit_events WHERE entity_type='REGISTRATION_IMPORT')"
        )
    ):
        raise RuntimeError(
            "OC104 downgrade blocked: import results and audit must be preserved"
        )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE registration_imports, audit_events IN SHARE ROW EXCLUSIVE MODE"
    )
    ensure_safe_downgrade(op.get_bind())
    catalog(PREVIOUS_EVENTS, PREVIOUS_ENTITIES)
    op.drop_table("registration_imports")
