"""load distributions

Revision ID: 20261007_0015
Revises: 20261007_0014
Create Date: 2026-10-07 14:36:06.324059
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261007_0015"
down_revision: str | None = "20261007_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INTEGRITY_TABLES = (
    "load_distributions",
    "load_distribution_orders",
    "load_distribution_parts",
    "load_distribution_volumes",
    "orders",
    "order_items",
    "load_plans",
    "load_plan_items",
    "load_plan_orders",
)
INTEGRITY_SQL = r"""CREATE FUNCTION validate_load_distributions() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d record; part_count integer; approved_count integer; canceled_count integer;
BEGIN
  FOR d IN SELECT id, status FROM load_distributions LOOP
    SELECT count(*), count(*) FILTER (WHERE status='APPROVED'),
      count(*) FILTER (WHERE status='CANCELED')
    INTO part_count, approved_count, canceled_count
    FROM load_distribution_parts WHERE distribution_id=d.id;
    IF part_count NOT BETWEEN 1 AND 10 OR
      NOT EXISTS (SELECT 1 FROM load_distribution_orders WHERE distribution_id=d.id) OR
      (SELECT count(*) FROM load_distribution_volumes WHERE distribution_id=d.id) NOT BETWEEN 1 AND 200 OR
      EXISTS (
        SELECT 1 FROM load_distribution_orders ldo JOIN order_items oi ON oi.order_id=ldo.order_id
        WHERE ldo.distribution_id=d.id AND
          (SELECT count(*) FROM load_distribution_volumes v
           WHERE v.distribution_id=d.id AND v.order_item_id=oi.id) <> oi.quantity
      ) OR EXISTS (
        SELECT 1 FROM load_distribution_volumes v JOIN order_items oi ON oi.id=v.order_item_id
        WHERE v.distribution_id=d.id AND v.snapshot_quantity <> oi.quantity
      ) THEN
      RAISE EXCEPTION 'invalid distribution coverage' USING ERRCODE='23514', CONSTRAINT='ck_load_distributions__integrity';
    END IF;
    IF EXISTS (
      SELECT 1 FROM load_distribution_parts p JOIN load_plans lp ON lp.id=p.load_plan_id
      WHERE p.distribution_id=d.id GROUP BY lp.truck_id HAVING count(*)>1
    ) OR EXISTS (
      SELECT 1 FROM load_distribution_parts p WHERE p.distribution_id=d.id AND (
        NOT EXISTS (SELECT 1 FROM load_distribution_volumes v WHERE v.part_id=p.id) OR
        EXISTS (
          (SELECT v.order_item_id, v.volume_index FROM load_distribution_volumes v WHERE v.part_id=p.id
           EXCEPT SELECT li.order_item_id, li.volume_index FROM load_plan_items li WHERE li.load_plan_id=p.load_plan_id AND li.placed)
          UNION ALL
          (SELECT li.order_item_id, li.volume_index FROM load_plan_items li WHERE li.load_plan_id=p.load_plan_id
           EXCEPT SELECT v.order_item_id, v.volume_index FROM load_distribution_volumes v WHERE v.part_id=p.id)
        ) OR EXISTS (
          (SELECT DISTINCT v.order_id FROM load_distribution_volumes v WHERE v.part_id=p.id
           EXCEPT SELECT lpo.order_id FROM load_plan_orders lpo WHERE lpo.load_plan_id=p.load_plan_id)
          UNION ALL
          (SELECT lpo.order_id FROM load_plan_orders lpo WHERE lpo.load_plan_id=p.load_plan_id
           EXCEPT SELECT DISTINCT v.order_id FROM load_distribution_volumes v WHERE v.part_id=p.id)
        )
      )
    ) THEN
      RAISE EXCEPTION 'invalid distribution partition' USING ERRCODE='23514', CONSTRAINT='ck_load_distributions__integrity';
    END IF;
    IF EXISTS (SELECT 1 FROM load_distribution_orders WHERE distribution_id=d.id AND active <> (d.status <> 'CANCELED')) OR
       EXISTS (SELECT 1 FROM load_distribution_volumes WHERE distribution_id=d.id AND active <> (d.status <> 'CANCELED')) OR
       (d.status='CANCELED' AND canceled_count<>part_count) OR
       (d.status='INCOMPLETE' AND canceled_count=0) OR
       (d.status='PROPOSED' AND (approved_count<>0 OR canceled_count<>0)) OR
       (d.status='PARTIALLY_APPROVED' AND (approved_count NOT BETWEEN 1 AND part_count-1 OR canceled_count<>0)) OR
       (d.status='APPROVED' AND approved_count<>part_count) OR
       EXISTS (
         SELECT 1 FROM load_distribution_parts p JOIN load_plans lp ON lp.id=p.load_plan_id
         WHERE p.distribution_id=d.id AND (
           (d.status='APPROVED' AND lp.status<>'APPROVED') OR
           (d.status<>'APPROVED' AND lp.status<>'CALCULATED') OR lp.unloaded_count<>0
         )
       ) OR EXISTS (
         SELECT 1 FROM load_distribution_orders ldo JOIN orders o ON o.id=ldo.order_id
         WHERE ldo.distribution_id=d.id AND d.status<>'CANCELED' AND (
           (d.status='APPROVED' AND o.status NOT IN ('PLANNED','IN_TRANSIT','DELIVERED')) OR
           (d.status<>'APPROVED' AND o.status<>'READY')
         )
       ) THEN
      RAISE EXCEPTION 'invalid distribution lifecycle' USING ERRCODE='23514', CONSTRAINT='ck_load_distributions__integrity';
    END IF;
  END LOOP;
  RETURN NULL;
END $$;
"""


def upgrade() -> None:
    op.create_table(
        "load_distributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'PARTIALLY_APPROVED', 'APPROVED', 'INCOMPLETE', 'CANCELED')",
            name=op.f("ck_load_distributions__status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_load_distributions__users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_load_distributions")),
    )
    op.create_table(
        "load_distribution_orders",
        sa.Column("distribution_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["distribution_id"],
            ["load_distributions.id"],
            name=op.f("fk_load_distribution_orders__load_distributions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_load_distribution_orders__orders"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "distribution_id", "order_id", name=op.f("pk_load_distribution_orders")
        ),
    )
    op.create_index(
        "uq_load_distribution_orders__active_order",
        "load_distribution_orders",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_table(
        "load_distribution_parts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("distribution_id", sa.Uuid(), nullable=False),
        sa.Column("load_plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'CANCELED')",
            name=op.f("ck_load_distribution_parts__status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["distribution_id"],
            ["load_distributions.id"],
            name=op.f("fk_load_distribution_parts__load_distributions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["load_plan_id"],
            ["load_plans.id"],
            name=op.f("fk_load_distribution_parts__load_plans"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_load_distribution_parts")),
        sa.UniqueConstraint(
            "id",
            "distribution_id",
            name=op.f("uq_load_distribution_parts__id_distribution_id"),
        ),
        sa.UniqueConstraint(
            "load_plan_id", name=op.f("uq_load_distribution_parts__load_plan_id")
        ),
    )
    op.create_index(
        op.f("ix_load_distribution_parts__distribution_id"),
        "load_distribution_parts",
        ["distribution_id"],
        unique=False,
    )
    op.create_table(
        "load_distribution_volumes",
        sa.Column("distribution_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("volume_index", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_quantity", sa.Integer(), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "volume_index BETWEEN 1 AND snapshot_quantity",
            name=op.f("ck_load_distribution_volumes__identity_range"),
        ),
        sa.ForeignKeyConstraint(
            ["distribution_id", "order_id"],
            [
                "load_distribution_orders.distribution_id",
                "load_distribution_orders.order_id",
            ],
            name="fk_load_distribution_volumes__distribution_order",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id", "order_id", "product_id"],
            ["order_items.id", "order_items.order_id", "order_items.product_id"],
            name="fk_load_distribution_volumes__provenance",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["part_id", "distribution_id"],
            ["load_distribution_parts.id", "load_distribution_parts.distribution_id"],
            name="fk_load_distribution_volumes__part",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "distribution_id",
            "order_item_id",
            "volume_index",
            name=op.f("pk_load_distribution_volumes"),
        ),
    )
    op.create_index(
        "ix_load_distribution_volumes__part_id",
        "load_distribution_volumes",
        ["part_id"],
        unique=False,
    )
    op.create_index(
        "uq_load_distribution_volumes__active_identity",
        "load_distribution_volumes",
        ["order_item_id", "volume_index"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.drop_constraint(
        op.f("ck_status_history__entity_type_allowed"), "status_history", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_status_history__entity_type_allowed"),
        "status_history",
        "entity_type IN ('ORDER','LOAD_PLAN','TRIP','DELIVERY','LOAD_DISTRIBUTION','LOAD_DISTRIBUTION_PART')",
    )
    op.execute(INTEGRITY_SQL)
    for table in INTEGRITY_TABLES:
        op.execute(
            f"CREATE CONSTRAINT TRIGGER validate_distribution_{table} AFTER INSERT OR UPDATE OR DELETE ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_load_distributions()"
        )


def downgrade() -> None:
    for table in INTEGRITY_TABLES:
        op.execute(f"DROP TRIGGER validate_distribution_{table} ON {table}")
    op.execute("DROP FUNCTION validate_load_distributions()")
    op.execute(
        "DELETE FROM status_history WHERE entity_type IN ('LOAD_DISTRIBUTION','LOAD_DISTRIBUTION_PART')"
    )
    op.drop_constraint(
        op.f("ck_status_history__entity_type_allowed"), "status_history", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_status_history__entity_type_allowed"),
        "status_history",
        "entity_type IN ('ORDER','LOAD_PLAN','TRIP','DELIVERY')",
    )
    op.drop_index(
        "uq_load_distribution_volumes__active_identity",
        table_name="load_distribution_volumes",
        postgresql_where=sa.text("active"),
    )
    op.drop_index(
        "ix_load_distribution_volumes__part_id", table_name="load_distribution_volumes"
    )
    op.drop_table("load_distribution_volumes")
    op.drop_index(
        op.f("ix_load_distribution_parts__distribution_id"),
        table_name="load_distribution_parts",
    )
    op.drop_table("load_distribution_parts")
    op.drop_index(
        "uq_load_distribution_orders__active_order",
        table_name="load_distribution_orders",
        postgresql_where=sa.text("active"),
    )
    op.drop_table("load_distribution_orders")
    op.drop_table("load_distributions")
