"""OC90: deliveries identify independent physical distribution legs.

Existing constraints still protect status, sequence and trip uniqueness. The
context trigger takes the Order lock to serialize cross-index assignments.
Distribution guards protect its structure once a delivery exists; shared
locks in the context trigger serialize those writes. Whole plan/order/item
snapshots freeze from LoadingSession or Trip, including legacy plans. Child
guards use parent NOWAIT to avoid inversion with loading checklist FK locks.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261020_0027"
down_revision = "20261020_0026"
branch_labels = None
depends_on = None

CONTEXT_SQL = """
CREATE FUNCTION validate_delivery_part_context() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE plan uuid; distribution uuid;
BEGIN
  IF TG_OP = 'UPDATE' AND
    (NEW.trip_id, NEW.order_id, NEW.distribution_part_id) IS DISTINCT FROM
    (OLD.trip_id, OLD.order_id, OLD.distribution_part_id) THEN
    RAISE EXCEPTION 'delivery context is immutable'
      USING ERRCODE='23514', CONSTRAINT='ck_deliveries__part_context';
  END IF;
  SELECT load_plan_id INTO plan FROM trips WHERE id=NEW.trip_id FOR SHARE;
  PERFORM 1 FROM orders WHERE id=NEW.order_id FOR UPDATE;
  IF NEW.distribution_part_id IS NULL THEN
    IF EXISTS (SELECT 1 FROM load_distribution_orders WHERE order_id=NEW.order_id AND active)
       OR EXISTS (SELECT 1 FROM load_distribution_parts WHERE load_plan_id=plan) THEN
      RAISE EXCEPTION 'distribution delivery requires a part'
        USING ERRCODE='23514', CONSTRAINT='ck_deliveries__part_context';
    END IF;
  ELSE
    SELECT p.distribution_id INTO distribution FROM load_distribution_parts p
      JOIN load_distributions d ON d.id=p.distribution_id
      JOIN load_plans lp ON lp.id=p.load_plan_id
      WHERE p.id=NEW.distribution_part_id AND p.load_plan_id=plan
        AND p.status='APPROVED' AND d.status='APPROVED' AND lp.status='APPROVED'
      FOR SHARE OF p,d;
    IF distribution IS NULL OR NOT EXISTS (
      SELECT 1 FROM load_distribution_volumes
      WHERE part_id=NEW.distribution_part_id AND order_id=NEW.order_id AND active
    ) THEN
      RAISE EXCEPTION 'delivery requires an approved current part containing the order'
        USING ERRCODE='23514', CONSTRAINT='ck_deliveries__part_context';
    END IF;
  END IF;
  IF EXISTS (
    SELECT 1 FROM deliveries e LEFT JOIN load_distribution_parts p ON p.id=e.distribution_part_id
    WHERE e.order_id=NEW.order_id AND e.id<>NEW.id AND (
      (e.distribution_part_id IS NULL) <> (NEW.distribution_part_id IS NULL)
      OR (NEW.distribution_part_id IS NOT NULL AND p.distribution_id<>distribution)
    )
  ) THEN
    RAISE EXCEPTION 'order cannot mix legacy deliveries or distributions'
      USING ERRCODE='23514', CONSTRAINT='ck_deliveries__assignment';
  END IF;
  RETURN NEW;
END $$;
"""

PARENT_SQL = """
CREATE FUNCTION protect_operational_distribution() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE identifier uuid;
BEGIN
  IF TG_OP='UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
  IF TG_TABLE_NAME='load_distributions' THEN
    identifier := OLD.id;
  ELSE
    identifier := COALESCE((to_jsonb(NEW)->>'distribution_id')::uuid,
                           (to_jsonb(OLD)->>'distribution_id')::uuid);
    -- Same lock used by delivery INSERT; also covers addition of a new part or volume.
    PERFORM 1 FROM load_distributions WHERE id=identifier FOR UPDATE;
  END IF;
  IF EXISTS (SELECT 1 FROM deliveries e JOIN load_distribution_parts p
             ON p.id=e.distribution_part_id WHERE p.distribution_id=identifier)
     OR (TG_OP='UPDATE' AND EXISTS (
       SELECT 1 FROM deliveries e JOIN load_distribution_parts p ON p.id=e.distribution_part_id
       WHERE p.distribution_id=(to_jsonb(OLD)->>'distribution_id')::uuid
     )) THEN
    RAISE EXCEPTION 'operational distribution is immutable'
      USING ERRCODE='23514', CONSTRAINT='ck_deliveries__part_context';
  END IF;
  IF TG_TABLE_NAME='load_distribution_parts' AND TG_OP<>'DELETE' THEN
    PERFORM 1 FROM load_plans WHERE id=NEW.load_plan_id FOR UPDATE;
    IF EXISTS (SELECT 1 FROM deliveries e JOIN trips t ON t.id=e.trip_id
               WHERE t.load_plan_id=NEW.load_plan_id) THEN
      RAISE EXCEPTION 'cannot attach an operated plan to a part'
        USING ERRCODE='23514', CONSTRAINT='ck_deliveries__part_context';
    END IF;
  END IF;
  IF TG_TABLE_NAME='load_distribution_orders' AND TG_OP<>'DELETE' THEN
    PERFORM 1 FROM orders WHERE id=NEW.order_id FOR UPDATE;
    IF NEW.active AND EXISTS (SELECT 1 FROM deliveries
                             WHERE order_id=NEW.order_id AND distribution_part_id IS NULL) THEN
      RAISE EXCEPTION 'order already has a legacy delivery'
        USING ERRCODE='23514', CONSTRAINT='ck_deliveries__assignment';
    END IF;
  END IF;
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION protect_trip_delivery_plan() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.load_plan_id IS DISTINCT FROM OLD.load_plan_id AND
     EXISTS (SELECT 1 FROM deliveries WHERE trip_id=OLD.id) THEN
    RAISE EXCEPTION 'trip delivery plan is immutable'
      USING ERRCODE='23514', CONSTRAINT='ck_deliveries__part_context';
  END IF;
  RETURN NEW;
END $$;
"""


SNAPSHOT_TABLES = ("load_plans", "load_plan_orders", "load_plan_items")
SNAPSHOT_SQL = """
CREATE FUNCTION protect_operated_load_plan() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE old_plan uuid; new_plan uuid; identifier uuid;
BEGIN
  IF TG_OP='UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
  IF TG_TABLE_NAME='load_plans' THEN
    old_plan := (to_jsonb(OLD)->>'id')::uuid;
    new_plan := (to_jsonb(NEW)->>'id')::uuid;
  ELSE
    old_plan := (to_jsonb(OLD)->>'load_plan_id')::uuid;
    new_plan := (to_jsonb(NEW)->>'load_plan_id')::uuid;
  END IF;
  FOR identifier IN SELECT DISTINCT value FROM unnest(ARRAY[old_plan,new_plan]) value
                    WHERE value IS NOT NULL ORDER BY value
  LOOP
    BEGIN
      -- Child tuples may already be locked. Never wait for a parent held by
      -- loading creation, which will acquire FK locks on these same items.
      PERFORM 1 FROM load_plans WHERE id=identifier FOR UPDATE NOWAIT;
    EXCEPTION WHEN lock_not_available THEN
      RAISE EXCEPTION 'load plan snapshot is busy; retry the transaction'
        USING ERRCODE='23514', CONSTRAINT='ck_load_plans__operational_snapshot';
    END;
    IF EXISTS (SELECT 1 FROM loading_sessions WHERE load_plan_id=identifier)
       OR EXISTS (SELECT 1 FROM trips WHERE load_plan_id=identifier) THEN
      RAISE EXCEPTION 'operated load plan snapshot is immutable'
        USING ERRCODE='23514', CONSTRAINT='ck_load_plans__operational_snapshot';
    END IF;
  END LOOP;
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
"""


def upgrade():
    op.add_column(
        "deliveries", sa.Column("distribution_part_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_deliveries__load_distribution_parts",
        "deliveries",
        "load_distribution_parts",
        ["distribution_part_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # OC87 already permitted operational single-part distributions.
    op.execute("""
        UPDATE deliveries e SET distribution_part_id=p.id
        FROM trips t JOIN load_distribution_parts p ON p.load_plan_id=t.load_plan_id
        WHERE e.trip_id=t.id
    """)
    op.drop_constraint("uq_deliveries__order_id", "deliveries", type_="unique")
    op.create_index(
        "uq_deliveries__legacy_order",
        "deliveries",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("distribution_part_id IS NULL"),
    )
    op.create_unique_constraint(
        "uq_deliveries__part_order", "deliveries", ["distribution_part_id", "order_id"]
    )
    op.execute(CONTEXT_SQL)
    op.execute("""
        CREATE TRIGGER validate_delivery_part_context
        BEFORE INSERT OR UPDATE OF trip_id,order_id,distribution_part_id ON deliveries
        FOR EACH ROW EXECUTE FUNCTION validate_delivery_part_context()
    """)
    # Validate backfilled AND legacy rows with the same authority as future
    # writes. Invalid pre-existing context aborts the transactional upgrade;
    # never silently bless a leg that does not transport the order.
    op.execute("UPDATE deliveries SET distribution_part_id=distribution_part_id")
    op.execute(PARENT_SQL)
    for table in (
        "load_distributions",
        "load_distribution_orders",
        "load_distribution_parts",
        "load_distribution_volumes",
    ):
        op.execute(f"""CREATE TRIGGER protect_operational_{table}
            BEFORE INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION protect_operational_distribution()""")
    op.execute("""CREATE TRIGGER protect_trip_delivery_plan
        BEFORE UPDATE OF load_plan_id ON trips
        FOR EACH ROW EXECUTE FUNCTION protect_trip_delivery_plan()""")

    op.execute(SNAPSHOT_SQL)
    for table in SNAPSHOT_TABLES:
        operations = (
            "UPDATE OR DELETE"
            if table == "load_plans"
            else "INSERT OR UPDATE OR DELETE"
        )
        op.execute(f"""CREATE TRIGGER protect_operated_{table}
            BEFORE {operations} ON {table}
            FOR EACH ROW EXECUTE FUNCTION protect_operated_load_plan()""")


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM deliveries WHERE distribution_part_id IS NOT NULL)"
            )
        )
        .scalar()
    ):
        raise RuntimeError(
            "OC90 downgrade blocked: distribution deliveries exist; preserve leg context and audit. "
            "Use a compensating migration; do not delete history."
        )
    for table in SNAPSHOT_TABLES:
        op.execute(f"DROP TRIGGER protect_operated_{table} ON {table}")
    op.execute("DROP FUNCTION protect_operated_load_plan()")
    op.execute("DROP TRIGGER protect_trip_delivery_plan ON trips")
    op.execute("DROP FUNCTION protect_trip_delivery_plan()")
    for table in (
        "load_distributions",
        "load_distribution_orders",
        "load_distribution_parts",
        "load_distribution_volumes",
    ):
        op.execute(f"DROP TRIGGER protect_operational_{table} ON {table}")
    op.execute("DROP FUNCTION protect_operational_distribution()")
    op.execute("DROP TRIGGER validate_delivery_part_context ON deliveries")
    op.execute("DROP FUNCTION validate_delivery_part_context()")
    op.drop_constraint("uq_deliveries__part_order", "deliveries", type_="unique")
    op.drop_index("uq_deliveries__legacy_order", table_name="deliveries")
    op.create_unique_constraint("uq_deliveries__order_id", "deliveries", ["order_id"])
    op.drop_constraint(
        "fk_deliveries__load_distribution_parts", "deliveries", type_="foreignkey"
    )
    op.drop_column("deliveries", "distribution_part_id")
