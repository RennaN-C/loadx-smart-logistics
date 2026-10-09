"""Fleet maintenance windows and optional odometer (OC100)."""

import sqlalchemy as sa
from alembic import op

revision = "20261009_0018"
down_revision = "20261008_0017"
branch_labels = None
depends_on = None
PREVIOUS_EVENTS = "'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED'"
PREVIOUS_ENTITIES = (
    "'USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS'"
)


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
    op.add_column("trucks", sa.Column("odometer_km", sa.BigInteger()))
    op.add_column("trucks", sa.Column("next_service_at", sa.DateTime(timezone=True)))
    op.add_column("trucks", sa.Column("next_service_km", sa.BigInteger()))
    for field, name in (
        ("odometer_km", "odometer_nonnegative"),
        ("next_service_km", "next_service_nonnegative"),
    ):
        op.create_check_constraint(
            op.f(f"ck_trucks__{name}"), "trucks", f"{field} IS NULL OR {field} >= 0"
        )
    op.create_table(
        "truck_maintenances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "truck_id",
            sa.Uuid(),
            sa.ForeignKey("trucks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("workshop", sa.String(160)),
        sa.Column("notes", sa.String(2000)),
        sa.Column("cost", sa.Numeric(12, 2)),
        sa.Column("odometer_km", sa.BigInteger()),
        sa.Column("completion_odometer_km", sa.BigInteger()),
        sa.Column("next_service_at", sa.DateTime(timezone=True)),
        sa.Column("next_service_km", sa.BigInteger()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("kind IN ('PREVENTIVE', 'CORRECTIVE')", name="kind_allowed"),
        sa.CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at", name="period_valid"
        ),
        sa.CheckConstraint("cost IS NULL OR cost >= 0", name="cost_nonnegative"),
        sa.CheckConstraint(
            "odometer_km IS NULL OR odometer_km >= 0", name="odometer_nonnegative"
        ),
        sa.CheckConstraint(
            "completion_odometer_km IS NULL OR completion_odometer_km >= 0",
            name="completion_odometer_nonnegative",
        ),
        sa.CheckConstraint(
            "next_service_km IS NULL OR next_service_km >= 0",
            name="next_service_nonnegative",
        ),
    )
    op.create_index(
        "ix_truck_maintenances__truck_period",
        "truck_maintenances",
        ["truck_id", "starts_at"],
    )
    catalog(
        f"{PREVIOUS_EVENTS}, 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED'",
        f"{PREVIOUS_ENTITIES}, 'TRUCK_MAINTENANCE'",
    )


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM truck_maintenances) OR EXISTS(SELECT 1 FROM trucks WHERE odometer_km IS NOT NULL OR next_service_at IS NOT NULL OR next_service_km IS NOT NULL) OR EXISTS(SELECT 1 FROM audit_events WHERE event_type IN ('MAINTENANCE_CREATED','MAINTENANCE_CLOSED','TRUCK_ODOMETER_UPDATED'))"
        )
    ):
        raise RuntimeError(
            "OC100 downgrade blocked: maintenance, odometer and audit must be preserved"
        )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE trucks, truck_maintenances, audit_events IN SHARE ROW EXCLUSIVE MODE"
    )
    ensure_safe_downgrade(op.get_bind())
    catalog(PREVIOUS_EVENTS, PREVIOUS_ENTITIES)
    op.drop_table("truck_maintenances")
    for name in ("odometer_nonnegative", "next_service_nonnegative"):
        op.drop_constraint(op.f(f"ck_trucks__{name}"), "trucks", type_="check")
    for name in ("odometer_km", "next_service_at", "next_service_km"):
        op.drop_column("trucks", name)
