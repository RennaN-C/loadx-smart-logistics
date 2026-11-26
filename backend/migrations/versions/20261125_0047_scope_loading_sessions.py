"""G06-B: tenant ownership and same-plan provenance for loading checklists.

Historical parents are proven legacy before organization backfill. Checklist
plan identity comes from its persisted session, never from an actor or input.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261125_0047"
down_revision = "20261119_0046"
branch_labels = None
depends_on = None

LEGACY = "00000000-0000-4000-8000-000000000301"


def _lock_sources() -> None:
    op.execute(
        sa.text(
            "LOCK TABLE loading_sessions, loading_session_items, load_plans, "
            "load_plan_items IN SHARE ROW EXCLUSIVE MODE"
        )
    )


def upgrade() -> None:
    _lock_sources()
    op.execute(
        sa.text(f"""
        DO $loadx_g06b$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM loading_sessions AS session
                LEFT JOIN load_plans AS plan ON plan.id = session.load_plan_id
                WHERE plan.id IS NULL
                   OR plan.organization_id <> CAST('{LEGACY}' AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM loading_session_items AS checklist
                LEFT JOIN loading_sessions AS session
                    ON session.id = checklist.loading_session_id
                LEFT JOIN load_plans AS plan ON plan.id = session.load_plan_id
                LEFT JOIN load_plan_items AS volume
                    ON volume.id = checklist.load_plan_item_id
                WHERE session.id IS NULL OR plan.id IS NULL OR volume.id IS NULL
                   OR volume.load_plan_id <> session.load_plan_id
                   OR volume.organization_id <> plan.organization_id
                   OR volume.organization_id <> CAST('{LEGACY}' AS uuid)
            ) THEN
                RAISE EXCEPTION 'G06-B upgrade refused: missing parent, non-legacy ownership or checklist volume from another plan or organization.';
            END IF;
        END
        $loadx_g06b$;
    """)
    )
    for table in ("loading_sessions", "loading_session_items"):
        op.add_column(
            table,
            sa.Column(
                "organization_id",
                sa.Uuid(),
                nullable=False,
                server_default=sa.text(f"'{LEGACY}'"),
            ),
        )
        op.alter_column(table, "organization_id", server_default=None)

    op.add_column(
        "loading_session_items", sa.Column("load_plan_id", sa.Uuid(), nullable=True)
    )
    # Loading tables have no snapshot-freezing trigger; the immutable plan and
    # its volumes are not updated. Locks keep their validated identities stable.
    op.execute(
        sa.text("""
        UPDATE loading_session_items AS checklist
        SET load_plan_id = session.load_plan_id
        FROM loading_sessions AS session
        WHERE session.id = checklist.loading_session_id
    """)
    )
    op.alter_column("loading_session_items", "load_plan_id", nullable=False)

    op.create_unique_constraint(
        "uq_load_plan_items__org_plan_id",
        "load_plan_items",
        ["organization_id", "load_plan_id", "id"],
    )
    op.create_unique_constraint(
        "uq_loading_sessions__org_id_plan",
        "loading_sessions",
        ["organization_id", "id", "load_plan_id"],
    )
    op.create_foreign_key(
        "fk_loading_sessions__organizations",
        "loading_sessions",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_loading_sessions__organization_plan",
        "loading_sessions",
        "load_plans",
        ["organization_id", "load_plan_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_loading_session_items__org_session_plan",
        "loading_session_items",
        "loading_sessions",
        ["organization_id", "loading_session_id", "load_plan_id"],
        ["organization_id", "id", "load_plan_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_loading_session_items__org_plan_item",
        "loading_session_items",
        "load_plan_items",
        ["organization_id", "load_plan_id", "load_plan_item_id"],
        ["organization_id", "load_plan_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    _lock_sources()
    op.execute(
        sa.text(f"""
        DO $loadx_g06b$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM loading_sessions
                WHERE organization_id <> CAST('{LEGACY}' AS uuid)
            ) OR EXISTS (
                SELECT 1 FROM loading_session_items
                WHERE organization_id <> CAST('{LEGACY}' AS uuid)
            ) THEN
                RAISE EXCEPTION 'G06-B downgrade refused: non-legacy loading records cannot be collapsed.';
            END IF;
        END
        $loadx_g06b$;
    """)
    )
    op.drop_constraint(
        "fk_loading_session_items__org_plan_item",
        "loading_session_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_loading_session_items__org_session_plan",
        "loading_session_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_loading_sessions__organization_plan", "loading_sessions", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_loading_sessions__organizations", "loading_sessions", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_loading_sessions__org_id_plan", "loading_sessions", type_="unique"
    )
    op.drop_constraint(
        "uq_load_plan_items__org_plan_id", "load_plan_items", type_="unique"
    )
    op.drop_column("loading_session_items", "load_plan_id")
    op.drop_column("loading_session_items", "organization_id")
    op.drop_column("loading_sessions", "organization_id")
