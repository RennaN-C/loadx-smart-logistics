"""G03-B2: global CNH and per-organization custom driver document types.

A second organization must remain non-operational until all domain-level
relations, routes, sessions, exports, and workers have been isolated.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0041"
down_revision = "20261115_0040"
branch_labels = None
depends_on = None

CNH = "00000000-0000-4000-8000-000000000102"
LEGACY = "00000000-0000-4000-8000-000000000301"
TYPE_TABLE = "driver_document_types"
CHILDREN = ("driver_documents", "driver_document_policies")

TYPE_CHECK = (
    f"(id = '{CNH}' AND organization_id IS NULL AND code = 'CNH') OR "
    f"(id <> '{CNH}' AND organization_id IS NOT NULL AND code <> 'CNH')"
)

DOC_CHECK = (
    f"(document_type_id = '{CNH}' AND document_type_organization_id IS NULL) OR "
    f"(document_type_id <> '{CNH}' AND "
    "document_type_organization_id = organization_id)"
)


def upgrade() -> None:
    op.add_column(
        TYPE_TABLE,
        sa.Column("organization_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_driver_document_types__organizations",
        TYPE_TABLE,
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # Only the seeded CNH is global. Previously created custom types belong
    # to the legacy organization, regardless of which user approved them.
    op.execute(
        f"""
        UPDATE {TYPE_TABLE}
        SET organization_id = '{LEGACY}'::uuid
        WHERE id <> '{CNH}'::uuid
        """
    )
    op.drop_constraint("uq_driver_document_types__code", TYPE_TABLE, type_="unique")
    op.create_unique_constraint(
        "uq_driver_document_types__organization_code",
        TYPE_TABLE,
        ["organization_id", "code"],
    )
    op.create_unique_constraint(
        "uq_driver_document_types__id_organization",
        TYPE_TABLE,
        ["id", "organization_id"],
    )
    op.create_check_constraint(
        "ck_driver_document_types__scope_valid", TYPE_TABLE, TYPE_CHECK
    )

    for table in CHILDREN:
        op.add_column(
            table,
            sa.Column("document_type_organization_id", sa.Uuid(), nullable=True),
        )
        # The ownership of each child was backfilled from its driver in 0040.
        # CNH remains global, custom types must match that very organization.
        op.execute(
            f"""
            UPDATE {table}
            SET document_type_organization_id = organization_id
            WHERE document_type_id <> '{CNH}'::uuid
            """
        )
        op.create_foreign_key(
            f"fk_{table}__type_org_scope",
            table,
            TYPE_TABLE,
            ["document_type_id", "document_type_organization_id"],
            ["id", "organization_id"],
            ondelete="RESTRICT",
        )
        op.create_check_constraint(f"ck_{table}__type_org_scope", table, DOC_CHECK)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            f"""
            SELECT EXISTS (
                SELECT 1 FROM {TYPE_TABLE}
                WHERE id <> CAST(:cnh AS uuid)
                  AND organization_id <> CAST(:legacy AS uuid)
            )
            """
        ),
        {"cnh": CNH, "legacy": LEGACY},
    ).scalar():
        raise RuntimeError(
            "G03-B2 downgrade refused: non-legacy custom document types "
            "cannot be collapsed into a global catalog."
        )

    for table in reversed(CHILDREN):
        op.drop_constraint(f"ck_{table}__type_org_scope", table, type_="check")
        op.drop_constraint(f"fk_{table}__type_org_scope", table, type_="foreignkey")
        op.drop_column(table, "document_type_organization_id")
    op.drop_constraint(
        "ck_driver_document_types__scope_valid", TYPE_TABLE, type_="check"
    )
    op.drop_constraint(
        "uq_driver_document_types__id_organization", TYPE_TABLE, type_="unique"
    )
    op.drop_constraint(
        "uq_driver_document_types__organization_code", TYPE_TABLE, type_="unique"
    )
    op.create_unique_constraint("uq_driver_document_types__code", TYPE_TABLE, ["code"])
    op.drop_constraint(
        "fk_driver_document_types__organizations", TYPE_TABLE, type_="foreignkey"
    )
    op.drop_column(TYPE_TABLE, "organization_id")
