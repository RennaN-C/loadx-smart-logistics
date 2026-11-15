"""G03-B1: scope fleet document, policy, and maintenance ownership.

Backfill derives organization_id exclusively from the owning driver/truck.
Second-organization operational access remains disabled until all domains and
the mixed driver-document-type catalog have been migrated.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0040"
down_revision = "20261115_0039"
branch_labels = None
depends_on = None

LEGACY_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000301"
LEGACY_DEFAULT = sa.text("'00000000-0000-4000-8000-000000000301'")
DEPENDENTS = (
    ("truck_maintenances", "trucks", "truck_id", "truck"),
    ("truck_documents", "trucks", "truck_id", "truck"),
    ("truck_document_policies", "trucks", "truck_id", "truck"),
    ("driver_documents", "drivers", "driver_id", "driver"),
    ("driver_document_policies", "drivers", "driver_id", "driver"),
)


def upgrade() -> None:
    for table, parent, parent_col, entity in DEPENDENTS:
        op.add_column(table, sa.Column("organization_id", sa.Uuid(), nullable=True))
        op.execute(
            f"""
            UPDATE {table} AS child
            SET organization_id = owner.organization_id
            FROM {parent} AS owner
            WHERE child.{parent_col} = owner.id
            """
        )
        # Nullable -> NOT NULL is a deliberate hard gate on orphan rows.
        op.alter_column(table, "organization_id", nullable=False)
        op.alter_column(table, "organization_id", server_default=LEGACY_DEFAULT)
        unique_name = f"uq_{table}__organization_id"
        op.create_unique_constraint(unique_name, table, ["organization_id", "id"])
        old_fk = f"fk_{table}__{parent}"
        op.drop_constraint(old_fk, table, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{table}__organization_{entity}",
            table,
            parent,
            ["organization_id", parent_col],
            ["organization_id", "id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    connection = op.get_bind()
    for table, _parent, _parent_col, _entity in DEPENDENTS:
        if connection.execute(
            sa.text(
                f"""
                SELECT EXISTS (
                    SELECT 1 FROM {table}
                    WHERE organization_id <> CAST(:legacy_id AS uuid)
                )
                """
            ),
            {"legacy_id": LEGACY_ORGANIZATION_ID},
        ).scalar():
            raise RuntimeError(
                f"G03-B1 downgrade blocked: {table} contains non-legacy records."
            )

    for table, parent, parent_col, entity in reversed(DEPENDENTS):
        scoped_fk = f"fk_{table}__organization_{entity}"
        op.drop_constraint(scoped_fk, table, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{table}__{parent}",
            table,
            parent,
            [parent_col],
            ["id"],
            ondelete="RESTRICT",
        )
        unique_name = f"uq_{table}__organization_id"
        op.drop_constraint(unique_name, table, type_="unique")
        op.drop_column(table, "organization_id")
