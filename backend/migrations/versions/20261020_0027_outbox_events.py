"""outbox_events

Revision ID: 20261020_0027
Revises: 20261020_0026
Create Date: 2026-10-20 17:48:45.475447
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261020_0027"
down_revision: str | None = "20261020_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NOW_SQL = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            sa.String(length=24),
            server_default="WHATSAPP_MOCK",
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("contract_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=96), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default="PENDING", nullable=False
        ),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("generation", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=NOW_SQL,
            nullable=False,
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=NOW_SQL,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=NOW_SQL,
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status = 'PROCESSING' AND lease_expires_at IS NOT NULL) OR (status <> 'PROCESSING' AND lease_expires_at IS NULL)",
            name=op.f("ck_outbox_events__lease_matches_status"),
        ),
        sa.CheckConstraint(
            "channel = 'WHATSAPP_MOCK' AND contract_version = 1",
            name=op.f("ck_outbox_events__contract_allowed"),
        ),
        sa.CheckConstraint(
            "event_type IN ('TRIP_STARTED','OCCURRENCE_REGISTERED')",
            name=op.f("ck_outbox_events__event_type_allowed"),
        ),
        sa.CheckConstraint(
            "last_error_code IS NULL OR last_error_code IN ('TRANSIENT', 'PERMANENT', 'TIMEOUT_UNKNOWN', 'UNKNOWN_RESULT', 'LEASE_EXPIRED', 'EXHAUSTED', 'LEGACY_FAILED', 'LEGACY_UNKNOWN', 'NO_RECIPIENT')",
            name=op.f("ck_outbox_events__error_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SUCCEEDED', 'RETRYABLE', 'TERMINAL', 'UNCERTAIN')",
            name=op.f("ck_outbox_events__status_allowed"),
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND generation >= attempt_count",
            name=op.f("ck_outbox_events__counters_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["operational_notifications.id"],
            name=op.f("fk_outbox_events__operational_notifications"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
        sa.UniqueConstraint(
            "idempotency_key", name=op.f("uq_outbox_events__idempotency_key")
        ),
        sa.UniqueConstraint(
            "notification_id", name=op.f("uq_outbox_events__notification_id")
        ),
    )
    op.create_index(
        "ix_outbox_events__created", "outbox_events", ["created_at", "id"], unique=False
    )
    op.create_index(
        "ix_outbox_events__status_due",
        "outbox_events",
        ["status", "next_attempt_at", "id"],
        unique=False,
    )
    op.create_table(
        "outbox_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("outbox_event_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column(
            "origin", sa.String(length=8), server_default="WORKER", nullable=False
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=NOW_SQL,
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.CheckConstraint(
            "(result = 'PROCESSING' AND finished_at IS NULL) OR (result <> 'PROCESSING' AND finished_at IS NOT NULL)",
            name=op.f("ck_outbox_attempts__finished_matches_result"),
        ),
        sa.CheckConstraint(
            "error_code IS NULL OR error_code IN ('TRANSIENT', 'PERMANENT', 'TIMEOUT_UNKNOWN', 'UNKNOWN_RESULT', 'LEASE_EXPIRED', 'EXHAUSTED', 'LEGACY_FAILED', 'LEGACY_UNKNOWN', 'NO_RECIPIENT')",
            name=op.f("ck_outbox_attempts__error_allowed"),
        ),
        sa.CheckConstraint(
            "origin IN ('LEGACY','WORKER')",
            name=op.f("ck_outbox_attempts__origin_allowed"),
        ),
        sa.CheckConstraint(
            "result IN ('PROCESSING','SUCCEEDED','RETRYABLE','TERMINAL','UNCERTAIN')",
            name=op.f("ck_outbox_attempts__result_allowed"),
        ),
        sa.CheckConstraint(
            "generation >= 0", name=op.f("ck_outbox_attempts__generation_valid")
        ),
        sa.ForeignKeyConstraint(
            ["outbox_event_id"],
            ["outbox_events.id"],
            name=op.f("fk_outbox_attempts__outbox_events"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_attempts")),
        sa.UniqueConstraint(
            "outbox_event_id",
            "generation",
            name=op.f("uq_outbox_attempts__outbox_event_id_generation"),
        ),
    )
    op.create_table(
        "outbox_retry_commands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("outbox_event_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=NOW_SQL,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_outbox_retry_commands__users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["outbox_event_id"],
            ["outbox_events.id"],
            name=op.f("fk_outbox_retry_commands__outbox_events"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_retry_commands")),
    )

    audit_checks(True)
    # Associate existing facts without calling any transport or changing OC84 states.
    op.execute("""
        INSERT INTO outbox_events(id, notification_id, event_type, correlation_id, idempotency_key, status, last_error_code)
        SELECT gen_random_uuid(), id, event_type, correlation_id,
               'notification:' || id || ':WHATSAPP_MOCK:v1',
               CASE mock_status WHEN 'NOT_ATTEMPTED' THEN 'PENDING'
                    WHEN 'ATTEMPT_CLAIMED' THEN 'UNCERTAIN' WHEN 'FAILED' THEN 'TERMINAL' ELSE 'SUCCEEDED' END,
               CASE mock_status WHEN 'ATTEMPT_CLAIMED' THEN 'LEGACY_UNKNOWN'
                    WHEN 'FAILED' THEN 'LEGACY_FAILED' WHEN 'NO_RECIPIENT' THEN 'NO_RECIPIENT' END
        FROM operational_notifications;
        INSERT INTO outbox_attempts(id, outbox_event_id, generation, origin, started_at, finished_at, result, error_code)
        SELECT gen_random_uuid(), e.id, 0, 'LEGACY', n.claimed_at,
               coalesce(n.completed_at, clock_timestamp()), e.status, e.last_error_code
        FROM outbox_events e JOIN operational_notifications n ON n.id=e.notification_id
        WHERE n.mock_status <> 'NOT_ATTEMPTED';
    """)
    op.execute("""
        CREATE FUNCTION guard_outbox_event() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                PERFORM 1 FROM operational_notifications n
                WHERE n.id=NEW.notification_id AND n.event_type=NEW.event_type
                  AND n.correlation_id=NEW.correlation_id FOR SHARE;
                IF NOT FOUND OR NEW.idempotency_key <> 'notification:' || NEW.notification_id || ':WHATSAPP_MOCK:v1' THEN
                    RAISE EXCEPTION 'invalid outbox origin' USING ERRCODE='23514';
                END IF;
            ELSE
                IF ROW(NEW.id,NEW.notification_id,NEW.channel,NEW.event_type,NEW.contract_version,NEW.correlation_id,NEW.idempotency_key,NEW.created_at)
                    IS DISTINCT FROM ROW(OLD.id,OLD.notification_id,OLD.channel,OLD.event_type,OLD.contract_version,OLD.correlation_id,OLD.idempotency_key,OLD.created_at)
                   OR NEW.generation < OLD.generation THEN
                    RAISE EXCEPTION 'immutable outbox identity' USING ERRCODE='23514';
                END IF;
                IF NEW.status <> OLD.status AND NOT (
                    (OLD.status IN ('PENDING','RETRYABLE') AND NEW.status IN ('PROCESSING','SUCCEEDED','TERMINAL','UNCERTAIN')) OR
                    (OLD.status = 'PROCESSING' AND NEW.status IN ('SUCCEEDED','RETRYABLE','TERMINAL','UNCERTAIN')) OR
                    (OLD.status IN ('RETRYABLE','TERMINAL','UNCERTAIN') AND NEW.status = 'PENDING')
                ) THEN RAISE EXCEPTION 'invalid outbox transition' USING ERRCODE='23514'; END IF;
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER guard_outbox_event BEFORE INSERT OR UPDATE ON outbox_events
            FOR EACH ROW EXECUTE FUNCTION guard_outbox_event();
        CREATE FUNCTION guard_outbox_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.result <> 'PROCESSING' OR
               ROW(NEW.id,NEW.outbox_event_id,NEW.generation,NEW.origin,NEW.started_at)
               IS DISTINCT FROM ROW(OLD.id,OLD.outbox_event_id,OLD.generation,OLD.origin,OLD.started_at) THEN
                RAISE EXCEPTION 'immutable attempt history' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER guard_outbox_attempt BEFORE UPDATE ON outbox_attempts
            FOR EACH ROW EXECUTE FUNCTION guard_outbox_attempt();
    """)


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM outbox_events) OR EXISTS(SELECT 1 FROM audit_events WHERE event_type='OUTBOX_REPROCESSED')"
        )
    ):
        raise RuntimeError("OC109 downgrade refused: preserve outbox and audit history")
    op.execute(
        "DROP TRIGGER guard_outbox_attempt ON outbox_attempts; DROP FUNCTION guard_outbox_attempt(); DROP TRIGGER guard_outbox_event ON outbox_events; DROP FUNCTION guard_outbox_event();"
    )
    audit_checks(False)
    op.drop_table("outbox_retry_commands")
    op.drop_table("outbox_attempts")
    op.drop_index("ix_outbox_events__status_due", table_name="outbox_events")
    op.drop_index("ix_outbox_events__created", table_name="outbox_events")
    op.drop_table("outbox_events")


def audit_checks(new: bool) -> None:
    checks = (
        [
            "event_type IN ('PROFILE_CREATED', 'PROFILE_UPDATED', 'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED', 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED', 'TRUCK_DOCUMENT_CREATED', 'TRUCK_DOCUMENT_RENEWED', 'TRUCK_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_CREATED', 'DRIVER_DOCUMENT_RENEWED', 'DRIVER_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_TYPE_APPROVED', 'ATTACHMENT_REGISTERED', 'ATTACHMENT_REVOKED', 'IMPORT_COMPLETED', 'IMPORT_REJECTED', 'COMPANY_PROFILE_CREATED', 'COMPANY_PROFILE_UPDATED', 'OUTBOX_REPROCESSED')",
            "entity_type IN ('USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS', 'TRUCK_MAINTENANCE', 'TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY', 'DRIVER_DOCUMENT', 'DRIVER_DOCUMENT_POLICY', 'DRIVER_DOCUMENT_TYPE', 'ATTACHMENT', 'REGISTRATION_IMPORT', 'COMPANY_PROFILE', 'ACCESS_PROFILE', 'OUTBOX_EVENT')",
        ]
        if new
        else [
            "event_type IN ('PROFILE_CREATED', 'PROFILE_UPDATED', 'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED', 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED', 'TRUCK_DOCUMENT_CREATED', 'TRUCK_DOCUMENT_RENEWED', 'TRUCK_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_CREATED', 'DRIVER_DOCUMENT_RENEWED', 'DRIVER_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_TYPE_APPROVED', 'ATTACHMENT_REGISTERED', 'ATTACHMENT_REVOKED', 'IMPORT_COMPLETED', 'IMPORT_REJECTED', 'COMPANY_PROFILE_CREATED', 'COMPANY_PROFILE_UPDATED')",
            "entity_type IN ('USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS', 'TRUCK_MAINTENANCE', 'TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY', 'DRIVER_DOCUMENT', 'DRIVER_DOCUMENT_POLICY', 'DRIVER_DOCUMENT_TYPE', 'ATTACHMENT', 'REGISTRATION_IMPORT', 'COMPANY_PROFILE', 'ACCESS_PROFILE')",
        ]
    )
    for column, expression in zip(("event_type", "entity_type"), checks, strict=True):
        name = f"ck_audit_events__{column}_allowed"
        op.drop_constraint(op.f(name), "audit_events", type_="check")
        op.create_check_constraint(op.f(name), "audit_events", expression)
