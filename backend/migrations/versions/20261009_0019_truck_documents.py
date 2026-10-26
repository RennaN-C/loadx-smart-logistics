"""Truck document history and explicit eligibility policies (OC101)."""

from importlib import import_module

import sqlalchemy as sa
from alembic import op

revision = "20261009_0019"
down_revision = "20261009_0018"
branch_labels = None
depends_on = None
previous = import_module("migrations.versions.20261009_0018_truck_maintenance")
PREVIOUS_EVENTS = f"{previous.PREVIOUS_EVENTS}, 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED'"
PREVIOUS_ENTITIES = f"{previous.PREVIOUS_ENTITIES}, 'TRUCK_MAINTENANCE'"


def upgrade() -> None:
    op.create_table(
        "truck_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "truck_id",
            sa.Uuid(),
            sa.ForeignKey("trucks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("file_reference", sa.Uuid()),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "kind IN ('CRLV', 'LICENSING', 'INSURANCE')", name="kind_allowed"
        ),
        sa.CheckConstraint("length(trim(reference)) > 0", name="reference_required"),
        sa.CheckConstraint(
            "issued_at IS NULL OR expires_at IS NULL OR expires_at > issued_at",
            name="period_valid",
        ),
    )
    op.create_index(
        "uq_truck_documents__current_kind",
        "truck_documents",
        ["truck_id", "kind"],
        unique=True,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_index(
        "ix_truck_documents__truck_created",
        "truck_documents",
        ["truck_id", "created_at"],
    )
    op.create_table(
        "truck_document_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "truck_id",
            sa.Uuid(),
            sa.ForeignKey("trucks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="false"),
        sa.CheckConstraint(
            "kind IN ('CRLV', 'LICENSING', 'INSURANCE')", name="kind_allowed"
        ),
        sa.UniqueConstraint(
            "truck_id", "kind", name="uq_truck_document_policies__truck_kind"
        ),
    )
    previous.catalog(
        f"{PREVIOUS_EVENTS}, 'TRUCK_DOCUMENT_CREATED', 'TRUCK_DOCUMENT_RENEWED', 'TRUCK_DOCUMENT_POLICY_UPDATED'",
        f"{PREVIOUS_ENTITIES}, 'TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY'",
    )


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM truck_documents) OR EXISTS(SELECT 1 FROM truck_document_policies) OR EXISTS(SELECT 1 FROM audit_events WHERE entity_type IN ('TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY'))"
        )
    ):
        raise RuntimeError(
            "OC101 downgrade blocked: document history, policies and audit must be preserved"
        )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE trucks, truck_documents, truck_document_policies, audit_events IN SHARE ROW EXCLUSIVE MODE"
    )
    ensure_safe_downgrade(op.get_bind())
    previous.catalog(PREVIOUS_EVENTS, PREVIOUS_ENTITIES)
    op.drop_table("truck_document_policies")
    op.drop_table("truck_documents")
