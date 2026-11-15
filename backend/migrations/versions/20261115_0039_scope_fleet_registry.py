"""G03-A: scope driver and truck registries, preserving legacy operations.

Document/policy tables and operational trip relations are migrated in subsequent
groups; the second operational organization remains disabled.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0039"
down_revision = "20261115_0038"
branch_labels = None
depends_on = None

LEGACY_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000301"
LEGACY_DEFAULT = sa.text("'00000000-0000-4000-8000-000000000301'")


def upgrade() -> None:
    for table, unique_fields in (
        (
            "drivers",
            (
                ("document", "document"),
                ("license_number", "license_number"),
            ),
        ),
        ("trucks", (("plate", "plate"),)),
    ):
        op.add_column(
            table,
            sa.Column(
                "organization_id",
                sa.Uuid(),
                nullable=False,
                server_default=LEGACY_DEFAULT,
            ),
        )
        op.create_foreign_key(
            f"fk_{table}__organizations",
            table,
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_unique_constraint(
            f"uq_{table}__organization_id",
            table,
            ["organization_id", "id"],
        )
        for old_name, column in unique_fields:
            op.drop_constraint(f"uq_{table}__{old_name}", table, type_="unique")
            op.create_unique_constraint(
                f"uq_{table}__organization_{old_name}",
                table,
                ["organization_id", column],
            )

    # A driver linked through a membership must belong to that organization.
    op.drop_constraint(
        "fk_organization_memberships__drivers",
        "organization_memberships",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_organization_memberships__organization_driver",
        "organization_memberships",
        "drivers",
        ["organization_id", "driver_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM drivers
                WHERE organization_id <> CAST(:legacy_id AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM trucks
                WHERE organization_id <> CAST(:legacy_id AS uuid)
            )
            """
        ),
        {"legacy_id": LEGACY_ORGANIZATION_ID},
    ).scalar():
        raise RuntimeError(
            "G03 downgrade refused: fleet records from another organization "
            "must not be collapsed into the legacy fleet."
        )

    op.drop_constraint(
        "fk_organization_memberships__organization_driver",
        "organization_memberships",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_organization_memberships__drivers",
        "organization_memberships",
        "drivers",
        ["driver_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    for table, unique_fields in (
        ("trucks", (("plate", "plate"),)),
        (
            "drivers",
            (
                ("document", "document"),
                ("license_number", "license_number"),
            ),
        ),
    ):
        for old_name, column in unique_fields:
            op.drop_constraint(
                f"uq_{table}__organization_{old_name}",
                table,
                type_="unique",
            )
            unique_name = f"uq_{table}__{old_name}"
            op.create_unique_constraint(
                unique_name,
                table,
                [column],
            )
        unique_constraint = f"uq_{table}__organization_id"
        op.drop_constraint(unique_constraint, table, type_="unique")
        foreign_key = f"fk_{table}__organizations"
        op.drop_constraint(foreign_key, table, type_="foreignkey")
        op.drop_column(table, "organization_id")
