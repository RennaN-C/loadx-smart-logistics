"""Driver license history and explicit document policies (OC102)."""

import sqlalchemy as sa
from alembic import op

revision = "20261009_0020"
down_revision = "20261009_0019"
branch_labels = None
depends_on = None
CNH = "00000000-0000-4000-8000-000000000102"
PREVIOUS_EVENTS = "'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED', 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED', 'TRUCK_DOCUMENT_CREATED', 'TRUCK_DOCUMENT_RENEWED', 'TRUCK_DOCUMENT_POLICY_UPDATED'"
PREVIOUS_ENTITIES = "'USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS', 'TRUCK_MAINTENANCE', 'TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY'"


def catalog(events: str, entities: str) -> None:
    for name, expression in (
        ("event_type_allowed", f"event_type IN ({events})"),
        ("entity_type_allowed", f"entity_type IN ({entities})"),
    ):
        op.drop_constraint(
            op.f(f"ck_audit_events__{name}"), "audit_events", type_="check"
        )
        op.create_check_constraint(
            op.f(f"ck_audit_events__{name}"), "audit_events", expression
        )


def upgrade() -> None:
    op.add_column(
        "drivers", sa.Column("license_expires_at", sa.DateTime(timezone=True))
    )
    op.create_table(
        "driver_document_types",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.CheckConstraint(
            "length(trim(code)) > 0 AND length(trim(name)) > 0", name="labels_required"
        ),
    )
    op.create_table(
        "driver_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "driver_id",
            sa.Uuid(),
            sa.ForeignKey("drivers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_type_id",
            sa.Uuid(),
            sa.ForeignKey("driver_document_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "legacy_backfill", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("category", sa.String(8)),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("length(trim(reference)) > 0", name="reference_required"),
        sa.CheckConstraint(
            "issued_at IS NULL OR expires_at IS NULL OR expires_at > issued_at",
            name="period_valid",
        ),
    )
    op.create_index(
        "uq_driver_documents__current_type",
        "driver_documents",
        ["driver_id", "document_type_id"],
        unique=True,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_index(
        "ix_driver_documents__driver_created",
        "driver_documents",
        ["driver_id", "created_at"],
    )
    op.create_table(
        "driver_document_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "driver_id",
            sa.Uuid(),
            sa.ForeignKey("drivers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "document_type_id",
            sa.Uuid(),
            sa.ForeignKey("driver_document_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "allowed_categories",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(allowed_categories) = 'array'", name="categories_array"
        ),
        sa.UniqueConstraint(
            "driver_id",
            "document_type_id",
            name="uq_driver_document_policies__driver_type",
        ),
    )
    op.execute(
        f"INSERT INTO driver_document_types(id,code,name) VALUES ('{CNH}','CNH','CNH')"
    )
    op.execute(
        f"INSERT INTO driver_documents(id,driver_id,document_type_id,legacy_backfill,reference,category,created_at) SELECT md5('oc102:' || id::text)::uuid,id,'{CNH}',true,license_number,license_category,created_at FROM drivers"
    )
    catalog(
        f"{PREVIOUS_EVENTS}, 'DRIVER_DOCUMENT_CREATED', 'DRIVER_DOCUMENT_RENEWED', 'DRIVER_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_TYPE_APPROVED'",
        f"{PREVIOUS_ENTITIES}, 'DRIVER_DOCUMENT', 'DRIVER_DOCUMENT_POLICY', 'DRIVER_DOCUMENT_TYPE'",
    )


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(
        sa.text(
            f"SELECT EXISTS(SELECT 1 FROM drivers WHERE license_expires_at IS NOT NULL) OR EXISTS(SELECT 1 FROM driver_document_policies) OR EXISTS(SELECT 1 FROM driver_document_types WHERE id != '{CNH}' OR code != 'CNH' OR name != 'CNH') OR EXISTS(SELECT 1 FROM driver_documents d JOIN drivers r ON r.id=d.driver_id WHERE NOT d.legacy_backfill OR d.document_type_id != '{CNH}' OR d.reference IS DISTINCT FROM r.license_number OR d.category IS DISTINCT FROM r.license_category OR d.issued_at IS NOT NULL OR d.expires_at IS NOT NULL OR d.superseded_at IS NOT NULL OR d.created_at IS DISTINCT FROM r.created_at) OR EXISTS(SELECT 1 FROM audit_events WHERE entity_type IN ('DRIVER_DOCUMENT','DRIVER_DOCUMENT_POLICY','DRIVER_DOCUMENT_TYPE'))"
        )
    ):
        raise RuntimeError(
            "OC102 downgrade blocked: driver document history, policy and audit must be preserved"
        )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE drivers, driver_documents, driver_document_policies, driver_document_types, audit_events IN SHARE ROW EXCLUSIVE MODE"
    )
    ensure_safe_downgrade(op.get_bind())
    catalog(PREVIOUS_EVENTS, PREVIOUS_ENTITIES)
    op.drop_table("driver_document_policies")
    op.drop_table("driver_documents")
    op.drop_table("driver_document_types")
    op.drop_column("drivers", "license_expires_at")
