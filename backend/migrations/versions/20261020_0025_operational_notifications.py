"""OC84: durable operational notifications and a single claimed mock attempt."""

import sqlalchemy as sa
from alembic import op

revision = "20261020_0025"
down_revision = "20261016_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("status_history_id", sa.Uuid()),
        sa.Column("occurrence_id", sa.Uuid()),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_driver_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "mock_status", sa.String(24), server_default="NOT_ATTEMPTED", nullable=False
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["status_history_id"], ["status_history.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"], ["occurrences.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["recipient_driver_id"], ["drivers.id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "(event_type = 'TRIP_STARTED' AND status_history_id IS NOT NULL AND occurrence_id IS NULL) OR (event_type = 'OCCURRENCE_REGISTERED' AND occurrence_id IS NOT NULL AND status_history_id IS NULL)",
            name="origin_matches_event",
        ),
        sa.CheckConstraint(
            "mock_status IN ('NOT_ATTEMPTED','ATTEMPT_CLAIMED','SIMULATED','FAILED','NO_RECIPIENT')",
            name="mock_status_allowed",
        ),
        sa.CheckConstraint(
            "(mock_status = 'NOT_ATTEMPTED' AND claimed_at IS NULL AND completed_at IS NULL) OR (mock_status = 'ATTEMPT_CLAIMED' AND claimed_at IS NOT NULL AND completed_at IS NULL) OR (mock_status IN ('SIMULATED','FAILED','NO_RECIPIENT') AND claimed_at IS NOT NULL AND completed_at IS NOT NULL)",
            name="attempt_timestamps",
        ),
    )
    op.create_index(
        "uq_operational_notifications__history_recipient",
        "operational_notifications",
        ["event_type", "status_history_id", "recipient_driver_id"],
        unique=True,
        postgresql_where=sa.text("status_history_id IS NOT NULL"),
    )
    op.create_index(
        "uq_operational_notifications__occurrence_recipient",
        "operational_notifications",
        ["event_type", "occurrence_id", "recipient_driver_id"],
        unique=True,
        postgresql_where=sa.text("occurrence_id IS NOT NULL"),
    )
    op.create_index(
        "ix_operational_notifications__trip_created",
        "operational_notifications",
        ["trip_id", "created_at", "id"],
    )
    op.execute("""
    CREATE FUNCTION check_operational_notification() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'INSERT' THEN
        PERFORM 1 FROM trips WHERE id=NEW.trip_id AND driver_id=NEW.recipient_driver_id FOR UPDATE;
        IF NOT FOUND OR NEW.mock_status <> 'NOT_ATTEMPTED' THEN
          RAISE EXCEPTION 'invalid notification recipient or initial state' USING ERRCODE='23514';
        END IF;
        IF NEW.event_type = 'TRIP_STARTED' THEN
          PERFORM 1 FROM status_history WHERE id=NEW.status_history_id AND entity_type='TRIP'
            AND entity_id=NEW.trip_id AND old_status='SCHEDULED' AND new_status='IN_ROUTE' FOR SHARE;
        ELSE
          PERFORM 1 FROM occurrences WHERE id=NEW.occurrence_id AND trip_id=NEW.trip_id FOR SHARE;
        END IF;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'invalid notification origin' USING ERRCODE='23514';
        END IF;
      ELSE
        IF (NEW.id,NEW.event_type,NEW.status_history_id,NEW.occurrence_id,NEW.trip_id,NEW.recipient_driver_id,NEW.correlation_id,NEW.created_at)
          IS DISTINCT FROM (OLD.id,OLD.event_type,OLD.status_history_id,OLD.occurrence_id,OLD.trip_id,OLD.recipient_driver_id,OLD.correlation_id,OLD.created_at) THEN
          RAISE EXCEPTION 'notification identity is immutable' USING ERRCODE='23514';
        END IF;
        IF NEW.mock_status <> OLD.mock_status AND NOT (
          (OLD.mock_status='NOT_ATTEMPTED' AND NEW.mock_status='ATTEMPT_CLAIMED') OR
          (OLD.mock_status='ATTEMPT_CLAIMED' AND NEW.mock_status IN ('SIMULATED','FAILED','NO_RECIPIENT'))) THEN
          RAISE EXCEPTION 'invalid notification attempt transition' USING ERRCODE='23514';
        END IF;
        IF OLD.claimed_at IS NOT NULL AND NEW.claimed_at IS DISTINCT FROM OLD.claimed_at THEN
          RAISE EXCEPTION 'notification claim is immutable' USING ERRCODE='23514';
        END IF;
        IF OLD.completed_at IS NOT NULL AND NEW.completed_at IS DISTINCT FROM OLD.completed_at THEN
          RAISE EXCEPTION 'notification result is immutable' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER operational_notification_guard BEFORE INSERT OR UPDATE ON operational_notifications
      FOR EACH ROW EXECUTE FUNCTION check_operational_notification();
    """)

    op.execute("""
    CREATE FUNCTION guard_operational_notification_source() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME='status_history' THEN
        IF (NEW.entity_type,NEW.entity_id,NEW.old_status,NEW.new_status) IS DISTINCT FROM
           (OLD.entity_type,OLD.entity_id,OLD.old_status,OLD.new_status) AND
           EXISTS(SELECT 1 FROM operational_notifications WHERE status_history_id=OLD.id) THEN
          RAISE EXCEPTION 'referenced notification history is immutable' USING ERRCODE='23514';
        END IF;
      ELSE
        IF NEW.trip_id IS DISTINCT FROM OLD.trip_id AND
           EXISTS(SELECT 1 FROM operational_notifications WHERE occurrence_id=OLD.id) THEN
          RAISE EXCEPTION 'referenced notification occurrence is immutable' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER notification_history_source_guard BEFORE UPDATE ON status_history
      FOR EACH ROW EXECUTE FUNCTION guard_operational_notification_source();
    CREATE TRIGGER notification_occurrence_source_guard BEFORE UPDATE ON occurrences
      FOR EACH ROW EXECUTE FUNCTION guard_operational_notification_source();
    """)


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(
        sa.text("SELECT EXISTS(SELECT 1 FROM operational_notifications)")
    ):
        raise RuntimeError(
            "OC84 downgrade blocked: durable notifications must be preserved"
        )


def downgrade() -> None:
    ensure_safe_downgrade(op.get_bind())
    op.execute("DROP TRIGGER notification_history_source_guard ON status_history")
    op.execute("DROP TRIGGER notification_occurrence_source_guard ON occurrences")
    op.execute("DROP FUNCTION guard_operational_notification_source()")
    op.execute(
        "DROP TRIGGER operational_notification_guard ON operational_notifications"
    )
    op.execute("DROP FUNCTION check_operational_notification()")
    op.drop_table("operational_notifications")
