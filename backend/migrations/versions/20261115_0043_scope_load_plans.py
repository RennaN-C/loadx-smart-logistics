"""G05-A: tenant ownership of load plans and recalculation lineage.

Only the plan header is migrated here. Plan orders/items, distributions,
optimizer idempotency, trips and storage require the following tenant groups.
Second-organization operation stays disabled until all gates pass.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0043"
down_revision = "20261115_0042"
branch_labels = None
depends_on = None

LEGACY_ID = "00000000-0000-4000-8000-000000000301"
LEGACY_DEFAULT = sa.text("'00000000-0000-4000-8000-000000000301'")


def upgrade() -> None:
    # All current operational trucks must belong to the legacy company.
    # Verify the actual recorded owner of each existing plan's truck;
    # do not infer ownership from its creator or silently migrate foreign data.
    # Server-side preflight works in online migrations and offline SQL.
    op.execute(
        sa.text(
            f"""
            DO $loadx_g05a$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM load_plans AS plan
                    JOIN trucks AS truck ON truck.id = plan.truck_id
                    WHERE truck.organization_id <> CAST('{LEGACY_ID}' AS uuid)
                ) THEN
                    RAISE EXCEPTION 'G05-A upgrade refused: a non-legacy truck owns an existing plan.';
                END IF;
            END
            $loadx_g05a$;
            """
        )
    )

    # The checked legacy ownership permits a NOT NULL DEFAULT backfill,
    # avoiding UPDATE followed by ALTER on a table with RI triggers.
    op.add_column(
        "load_plans",
        sa.Column(
            "organization_id",
            sa.Uuid(),
            nullable=False,
            server_default=LEGACY_DEFAULT,
        ),
    )
    op.create_foreign_key(
        "fk_load_plans__organizations",
        "load_plans",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_load_plans__organization_id",
        "load_plans",
        ["organization_id", "id"],
    )
    op.drop_constraint("fk_load_plans__trucks", "load_plans", type_="foreignkey")
    op.drop_constraint("fk_load_plans__load_plans", "load_plans", type_="foreignkey")
    op.create_foreign_key(
        "fk_load_plans__organization_truck",
        "load_plans",
        "trucks",
        ["organization_id", "truck_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_load_plans__organization_recalculated_from",
        "load_plans",
        "load_plans",
        ["organization_id", "recalculated_from_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Refuse to collapse multi-tenant data on downgrade; offline-safe.
    op.execute(
        sa.text(
            f"""
            DO $loadx_g05a$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM load_plans
                    WHERE organization_id <> CAST('{LEGACY_ID}' AS uuid)
                ) THEN
                    RAISE EXCEPTION 'G05-A downgrade refused: non-legacy plans or recalculations cannot be collapsed into the legacy organization.';
                END IF;
            END
            $loadx_g05a$;
            """
        )
    )

    op.drop_constraint(
        "fk_load_plans__organization_recalculated_from",
        "load_plans",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_load_plans__organization_truck", "load_plans", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_load_plans__load_plans",
        "load_plans",
        "load_plans",
        ["recalculated_from_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_load_plans__trucks",
        "load_plans",
        "trucks",
        ["truck_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("uq_load_plans__organization_id", "load_plans", type_="unique")
    op.drop_constraint("fk_load_plans__organizations", "load_plans", type_="foreignkey")
    op.drop_column("load_plans", "organization_id")
