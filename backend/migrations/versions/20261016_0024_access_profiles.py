"""OC112: explicit permissions and custom standalone profiles."""

import sqlalchemy as sa
from alembic import op

revision = "20261016_0024"
down_revision = "20261009_0023"
branch_labels = None
depends_on = None

CATALOG = [
    ("loadx.customers.read", True),
    ("loadx.customers.manage", True),
    ("loadx.products.read", True),
    ("loadx.products.manage", True),
    ("loadx.trucks.read", True),
    ("loadx.trucks.manage", True),
    ("loadx.drivers.read", True),
    ("loadx.drivers.manage", True),
    ("loadx.orders.read", True),
    ("loadx.orders.manage", True),
    ("loadx.planning.read", True),
    ("loadx.planning.create", True),
    ("loadx.planning.approve", True),
    ("loadx.loading.read", True),
    ("loadx.loading.create", True),
    ("loadx.loading.operate", True),
    ("loadx.trips.read", True),
    ("loadx.trips.manage", True),
    ("loadx.deliveries.read", True),
    ("loadx.deliveries.manage", True),
    ("loadx.occurrences.read", True),
    ("loadx.occurrences.manage", True),
    ("loadx.reports.read", True),
    ("loadx.messages.manage", True),
    ("loadx.audit.read", False),
    ("loadx.users.manage", False),
    ("loadx.profiles.manage", False),
    ("loadx.settings.manage", False),
    ("loadx.integrations.read", False),
    ("loadx.imports.manage", False),
    ("loadx.trips.own", False),
]
EVENTS = "event_type IN ('PROFILE_CREATED', 'PROFILE_UPDATED', 'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED', 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED', 'TRUCK_DOCUMENT_CREATED', 'TRUCK_DOCUMENT_RENEWED', 'TRUCK_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_CREATED', 'DRIVER_DOCUMENT_RENEWED', 'DRIVER_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_TYPE_APPROVED', 'ATTACHMENT_REGISTERED', 'ATTACHMENT_REVOKED', 'IMPORT_COMPLETED', 'IMPORT_REJECTED', 'COMPANY_PROFILE_CREATED', 'COMPANY_PROFILE_UPDATED')"
ENTITIES = "entity_type IN ('USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS', 'TRUCK_MAINTENANCE', 'TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY', 'DRIVER_DOCUMENT', 'DRIVER_DOCUMENT_POLICY', 'DRIVER_DOCUMENT_TYPE', 'ATTACHMENT', 'REGISTRATION_IMPORT', 'COMPANY_PROFILE', 'ACCESS_PROFILE')"


def audit_constraints(events, entities):
    for field, condition in (("event_type", events), ("entity_type", entities)):
        name = f"ck_audit_events__{field}_allowed"
        op.drop_constraint(op.f(name), "audit_events", type_="check")
        op.create_check_constraint(op.f(name), "audit_events", condition)


def upgrade():
    op.create_table(
        "access_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("name_key", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("name_key"),
        sa.CheckConstraint("version > 0", name="positive_version"),
        sa.CheckConstraint(
            "name_key = lower(trim(name)) AND length(name_key) > 0",
            name="normalized_name",
        ),
    )
    op.create_table(
        "access_permissions",
        sa.Column("code", sa.String(80), primary_key=True),
        sa.Column("delegable", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("code", "delegable"),
    )
    table = sa.table(
        "access_permissions",
        sa.column("code", sa.String()),
        sa.column("delegable", sa.Boolean()),
    )
    op.bulk_insert(
        table, [{"code": code, "delegable": delegable} for code, delegable in CATALOG]
    )
    op.create_table(
        "access_profile_permissions",
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("access_profiles.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("permission_code", sa.String(80), primary_key=True),
        sa.Column("delegable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["permission_code", "delegable"],
            ["access_permissions.code", "access_permissions.delegable"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("delegable = true", name="delegable_only"),
    )
    op.add_column("users", sa.Column("custom_profile_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users__access_profiles",
        "users",
        "access_profiles",
        ["custom_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_users__custom_profile_id", "users", ["custom_profile_id"])
    op.drop_constraint(op.f("ck_users__role_allowed"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users__role_allowed"),
        "users",
        "role IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER', 'CUSTOM')",
    )
    op.create_check_constraint(
        op.f("ck_users__custom_profile_role"),
        "users",
        "(role = 'CUSTOM') = (custom_profile_id IS NOT NULL)",
    )
    audit_constraints(EVENTS, ENTITIES)


def downgrade():
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM users WHERE role = 'CUSTOM') OR EXISTS (SELECT 1 FROM audit_events WHERE entity_type = 'ACCESS_PROFILE')"
        )
    ).scalar():
        raise RuntimeError(
            "Reassign custom users and retain/export profile audit before downgrade; history cannot be discarded."
        )
    audit_constraints(
        EVENTS.replace("'PROFILE_CREATED', 'PROFILE_UPDATED', ", ""),
        ENTITIES.replace(", 'ACCESS_PROFILE'", ""),
    )
    op.drop_constraint(op.f("ck_users__custom_profile_role"), "users", type_="check")
    op.drop_constraint(op.f("ck_users__role_allowed"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users__role_allowed"),
        "users",
        "role IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER')",
    )
    op.drop_index("ix_users__custom_profile_id", table_name="users")
    op.drop_constraint("fk_users__access_profiles", "users", type_="foreignkey")
    op.drop_column("users", "custom_profile_id")
    op.drop_table("access_profile_permissions")
    op.drop_table("access_permissions")
    op.drop_table("access_profiles")
