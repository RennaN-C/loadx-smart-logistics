"""OC110: attachments with protected resource references and audit."""

import sqlalchemy as sa
from alembic import op

revision = "20261009_0021"
down_revision = "20261009_0020"
branch_labels = None
depends_on = None

PREVIOUS_EVENTS = "'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED', 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED', 'TRUCK_DOCUMENT_CREATED', 'TRUCK_DOCUMENT_RENEWED', 'TRUCK_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_CREATED', 'DRIVER_DOCUMENT_RENEWED', 'DRIVER_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_TYPE_APPROVED'"
PREVIOUS_ENTITIES = "'USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS', 'TRUCK_MAINTENANCE', 'TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY', 'DRIVER_DOCUMENT', 'DRIVER_DOCUMENT_POLICY', 'DRIVER_DOCUMENT_TYPE'"


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
        "operational_attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        *(
            sa.Column(
                f"{resource}_id",
                sa.Uuid(),
                sa.ForeignKey(f"{table}.id", ondelete="RESTRICT"),
            )
            for resource, table in (
                ("order", "orders"),
                ("trip", "trips"),
                ("delivery", "deliveries"),
                ("occurrence", "occurrences"),
            )
        ),
        sa.Column(
            "recorded_by",
            sa.Uuid(),
            sa.ForeignKey(
                "users.id",
                ondelete="RESTRICT",
                name="fk_operational_attachments__recorded_by_users",
            ),
            nullable=False,
        ),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "revoked_by",
            sa.Uuid(),
            sa.ForeignKey(
                "users.id",
                ondelete="RESTRICT",
                name="fk_operational_attachments__revoked_by_users",
            ),
        ),
        sa.UniqueConstraint("recorded_by", "event_id"),
        sa.CheckConstraint(
            "num_nonnulls(order_id, trip_id, delivery_id, occurrence_id) = 1",
            name="exactly_one_resource",
        ),
        sa.CheckConstraint(
            "media_type IN ('image/png', 'image/jpeg')", name="media_type_allowed"
        ),
        sa.CheckConstraint("size_bytes BETWEEN 1 AND 5242880", name="size_allowed"),
        sa.CheckConstraint(
            "length(sha256) = 64 AND length(fingerprint) = 64", name="hash_lengths"
        ),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND revoked_at IS NULL AND revoked_by IS NULL) OR (status = 'REVOKED' AND revoked_at IS NOT NULL AND revoked_by IS NOT NULL)",
            name="revocation_consistent",
        ),
    )
    for resource in ("order", "trip", "delivery", "occurrence"):
        op.create_index(
            f"ix_operational_attachments__{resource}_recorded",
            "operational_attachments",
            [f"{resource}_id", "recorded_at", "id"],
        )
    catalog(
        f"{PREVIOUS_EVENTS}, 'ATTACHMENT_REGISTERED', 'ATTACHMENT_REVOKED'",
        f"{PREVIOUS_ENTITIES}, 'ATTACHMENT'",
    )


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM operational_attachments) OR EXISTS(SELECT 1 FROM audit_events WHERE entity_type='ATTACHMENT')"
        )
    ):
        raise RuntimeError(
            "OC110 downgrade blocked: attachment history and audit must be preserved"
        )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE operational_attachments, audit_events IN SHARE ROW EXCLUSIVE MODE"
    )
    ensure_safe_downgrade(op.get_bind())
    catalog(PREVIOUS_EVENTS, PREVIOUS_ENTITIES)
    op.drop_table("operational_attachments")
