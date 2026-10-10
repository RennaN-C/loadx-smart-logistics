"""OC91: cadastro institucional monoempresa."""

import sqlalchemy as sa
from alembic import op

revision = "20261009_0023"
down_revision = "20261009_0022"
branch_labels = None
depends_on = None
PREVIOUS_EVENTS = "'USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED', 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED', 'TRUCK_DOCUMENT_CREATED', 'TRUCK_DOCUMENT_RENEWED', 'TRUCK_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_CREATED', 'DRIVER_DOCUMENT_RENEWED', 'DRIVER_DOCUMENT_POLICY_UPDATED', 'DRIVER_DOCUMENT_TYPE_APPROVED', 'ATTACHMENT_REGISTERED', 'ATTACHMENT_REVOKED', 'IMPORT_COMPLETED', 'IMPORT_REJECTED'"
PREVIOUS_ENTITIES = "'USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS', 'TRUCK_MAINTENANCE', 'TRUCK_DOCUMENT', 'TRUCK_DOCUMENT_POLICY', 'DRIVER_DOCUMENT', 'DRIVER_DOCUMENT_POLICY', 'DRIVER_DOCUMENT_TYPE', 'ATTACHMENT', 'REGISTRATION_IMPORT'"


def catalog(events: str, entities: str) -> None:
    for field, values in (("event_type", events), ("entity_type", entities)):
        name = op.f(f"ck_audit_events__{field}_allowed")
        op.drop_constraint(name, "audit_events", type_="check")
        op.create_check_constraint(name, "audit_events", f"{field} IN ({values})")


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("legal_name", sa.String(160), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("cnpj", sa.String(14)),
        sa.Column("phone", sa.String(11)),
        sa.Column("email", sa.String(255)),
        sa.Column("logo_reference", sa.String(2048)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "id = '00000000-0000-0000-0000-000000000091'", name="singleton"
        ),
        sa.CheckConstraint(
            "length(trim(legal_name)) > 0 AND length(trim(display_name)) > 0",
            name="names_not_empty",
        ),
        sa.CheckConstraint("cnpj IS NULL OR cnpj ~ '^[0-9]{14}$'", name="cnpj_format"),
    )
    catalog(
        f"{PREVIOUS_EVENTS}, 'COMPANY_PROFILE_CREATED', 'COMPANY_PROFILE_UPDATED'",
        f"{PREVIOUS_ENTITIES}, 'COMPANY_PROFILE'",
    )


def ensure_safe_downgrade(connection: sa.Connection) -> None:
    if connection.scalar(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM company_profiles) OR EXISTS(SELECT 1 FROM audit_events WHERE entity_type='COMPANY_PROFILE')"
        )
    ):
        raise RuntimeError(
            "OC91 downgrade blocked: company profile and audit must be preserved"
        )


def downgrade() -> None:
    op.execute("LOCK TABLE company_profiles, audit_events IN SHARE ROW EXCLUSIVE MODE")
    ensure_safe_downgrade(op.get_bind())
    catalog(PREVIOUS_EVENTS, PREVIOUS_ENTITIES)
    op.drop_table("company_profiles")
