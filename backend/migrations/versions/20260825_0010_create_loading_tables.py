"""create loading tables

Revision ID: 20260825_0010
Revises: 20260825_0009
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0010"
down_revision: str | None = "20260825_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
def upgrade() -> None:
    op.create_table("loading_sessions", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("load_plan_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.ForeignKeyConstraint(["load_plan_id"], ["load_plans.id"], name=op.f("fk_loading_sessions__load_plans"), ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id", name=op.f("pk_loading_sessions")), sa.UniqueConstraint("load_plan_id", name=op.f("uq_loading_sessions__load_plan_id")))
    op.create_index(op.f("ix_loading_sessions__status"), "loading_sessions", ["status"])
    op.create_table("loading_session_items", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("loading_session_id", sa.Uuid(), nullable=False), sa.Column("load_plan_item_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.ForeignKeyConstraint(["loading_session_id"], ["loading_sessions.id"], name=op.f("fk_loading_session_items__loading_sessions"), ondelete="RESTRICT"), sa.ForeignKeyConstraint(["load_plan_item_id"], ["load_plan_items.id"], name=op.f("fk_loading_session_items__load_plan_items"), ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id", name=op.f("pk_loading_session_items")), sa.UniqueConstraint("loading_session_id", "load_plan_item_id", name=op.f("uq_loading_session_items__session_plan_item")))
    op.create_index(op.f("ix_loading_session_items__loading_session_id"), "loading_session_items", ["loading_session_id"])
    op.create_index(op.f("ix_loading_session_items__load_plan_item_id"), "loading_session_items", ["load_plan_item_id"])
def downgrade() -> None:
    op.drop_table("loading_session_items")
    op.drop_table("loading_sessions")
