"""OC103: personal recipients and notification preferences, preserving OC84 facts."""

import sqlalchemy as sa
from alembic import op

revision = "20261020_0026"
down_revision = "20261020_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_recipients",
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("notification_id", "user_id"),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["operational_notifications.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_notification_recipients__user_created",
        "notification_recipients",
        ["user_id", "created_at", "notification_id"],
    )
    op.create_index(
        "ix_notification_recipients__unread",
        "notification_recipients",
        ["user_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "category"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "category IN ('TRIPS','OCCURRENCES','SECURITY')", name="category_allowed"
        ),
        sa.CheckConstraint(
            "category <> 'SECURITY' OR enabled = true", name="security_required"
        ),
    )
    # Frozen cutover policy: current authorized accounts, not inferred historical recipients.
    op.execute("""
        INSERT INTO notification_recipients (notification_id, user_id)
        SELECT n.id, u.id FROM operational_notifications n
        JOIN trips t ON t.id=n.trip_id
        JOIN drivers d ON d.id=n.recipient_driver_id
        JOIN users u ON u.active AND (
          u.role IN ('ADMIN','LOGISTICS_MANAGER') OR
          (u.role='DRIVER' AND u.driver_id=n.recipient_driver_id AND t.driver_id=n.recipient_driver_id AND d.active) OR
          (u.role='CUSTOM' AND EXISTS (
            SELECT 1 FROM access_profiles p WHERE p.id=u.custom_profile_id AND p.active
              AND EXISTS (SELECT 1 FROM access_profile_permissions g WHERE g.profile_id=p.id AND g.permission_code='loadx.trips.read')
              AND (n.event_type='TRIP_STARTED' OR EXISTS (
                SELECT 1 FROM access_profile_permissions g WHERE g.profile_id=p.id AND g.permission_code='loadx.occurrences.read'
              ))
          ))
        )
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        CREATE FUNCTION guard_notification_recipient() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF (NEW.notification_id,NEW.user_id,NEW.created_at) IS DISTINCT FROM
             (OLD.notification_id,OLD.user_id,OLD.created_at) OR
             (OLD.read_at IS NOT NULL AND NEW.read_at IS DISTINCT FROM OLD.read_at) THEN
            RAISE EXCEPTION 'notification recipient and first read are immutable' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER notification_recipient_guard BEFORE UPDATE ON notification_recipients
          FOR EACH ROW EXECUTE FUNCTION guard_notification_recipient();
    """)


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM notification_recipients) OR EXISTS(SELECT 1 FROM notification_preferences)"
        )
    ):
        raise RuntimeError(
            "OC103 downgrade blocked: recipients, reading and preferences must be preserved"
        )


def downgrade() -> None:
    ensure_safe_downgrade(op.get_bind())
    op.execute("DROP TRIGGER notification_recipient_guard ON notification_recipients")
    op.execute("DROP FUNCTION guard_notification_recipient()")
    op.drop_table("notification_preferences")
    op.drop_table("notification_recipients")
