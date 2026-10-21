"""OC94: narrowly permit cancellation/replacement of an operated load part.

Revision ID: 20261021_0034
Revises: 20261021_0033

OC90 normally freezes all physical distribution structures once a delivery
exists. This migration only permits audited lifecycle changes backed by an
actually canceled trip, without allowing volume or identity modifications.
"""

from collections.abc import Sequence
from importlib import import_module

from alembic import op

revision: str = "20261021_0034"
down_revision: str | None = "20261021_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GUARD_SQL = """
CREATE OR REPLACE FUNCTION protect_operational_distribution()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  identifier uuid;
BEGIN
  IF TG_OP = 'UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN
    RETURN NEW;
  END IF;
  IF TG_TABLE_NAME = 'load_distributions' THEN
    identifier := OLD.id;
  ELSE
    identifier := COALESCE((to_jsonb(NEW)->>'distribution_id')::uuid,
                           (to_jsonb(OLD)->>'distribution_id')::uuid);
    PERFORM 1 FROM load_distributions WHERE id = identifier FOR UPDATE;
  END IF;

  -- Only the lifecycle status may change after the trip has been canceled.
  -- The original deliveries, order identities and physical volumes stay put.
  IF TG_TABLE_NAME = 'load_distribution_parts' AND TG_OP = 'UPDATE'
     AND (to_jsonb(NEW) - 'status' - 'load_plan_id')
           = (to_jsonb(OLD) - 'status' - 'load_plan_id')
  THEN
    IF OLD.status = 'APPROVED' AND NEW.status = 'CANCELED'
       AND NEW.load_plan_id = OLD.load_plan_id
       AND EXISTS (SELECT 1 FROM trips t
                   WHERE t.load_plan_id = OLD.load_plan_id
                     AND t.status = 'CANCELED')
       AND NOT EXISTS (SELECT 1 FROM deliveries e JOIN trips t
                       ON t.id = e.trip_id
                       WHERE t.load_plan_id = OLD.load_plan_id
                         AND e.status <> 'CANCELED')
       AND NOT EXISTS (SELECT 1 FROM loading_sessions s
                       WHERE s.load_plan_id = OLD.load_plan_id)
    THEN
      RETURN NEW;
    END IF;
    -- An operated, canceled leg may be replaced with a NEW calculated plan
    -- whose provenance points at the canceled original; never repoint a live
    -- operation, delete the old trip, or mutate its volume identities.
    IF OLD.status = 'CANCELED' AND NEW.status = 'PENDING'
       AND NEW.load_plan_id <> OLD.load_plan_id
       AND EXISTS (
           SELECT 1 FROM load_plans lp JOIN trips t
             ON t.load_plan_id = lp.recalculated_from_id
           WHERE lp.id = NEW.load_plan_id
             AND lp.status = 'CALCULATED' AND t.status = 'CANCELED'
             AND t.load_plan_id = OLD.load_plan_id
       )
       AND NOT EXISTS (
           SELECT 1 FROM deliveries e JOIN trips t ON t.id = e.trip_id
           WHERE t.load_plan_id = OLD.load_plan_id
             AND e.status <> 'CANCELED'
       )
    THEN
      RETURN NEW;
    END IF;
    IF OLD.status = 'PENDING' AND NEW.status = 'APPROVED'
       AND NEW.load_plan_id = OLD.load_plan_id
       AND EXISTS (
           SELECT 1 FROM load_plans lp JOIN trips t
             ON t.load_plan_id = lp.recalculated_from_id
           WHERE lp.id = NEW.load_plan_id
             AND lp.status IN ('CALCULATED','APPROVED')
             AND t.status = 'CANCELED'
       )
    THEN
      RETURN NEW;
    END IF;
  END IF;

  IF TG_TABLE_NAME = 'load_distributions' AND TG_OP = 'UPDATE'
     AND (to_jsonb(NEW) - 'status') = (to_jsonb(OLD) - 'status')
  THEN
    IF OLD.status = 'APPROVED' AND NEW.status = 'INCOMPLETE'
       AND EXISTS (
           SELECT 1 FROM load_distribution_parts p
           WHERE p.distribution_id = OLD.id AND p.status = 'CANCELED'
       )
    THEN RETURN NEW; END IF;
    IF OLD.status = 'INCOMPLETE'
       AND NEW.status IN ('PARTIALLY_APPROVED','PROPOSED')
       AND NOT EXISTS (
           SELECT 1 FROM load_distribution_parts p
           WHERE p.distribution_id = OLD.id AND p.status = 'CANCELED'
       )
       AND EXISTS (
           SELECT 1 FROM load_distribution_parts p JOIN load_plans lp
             ON lp.id = p.load_plan_id JOIN trips t
             ON t.load_plan_id = lp.recalculated_from_id
           WHERE p.distribution_id = OLD.id AND t.status = 'CANCELED'
       )
    THEN RETURN NEW; END IF;
    IF OLD.status IN ('PARTIALLY_APPROVED','PROPOSED','INCOMPLETE')
       AND NEW.status = 'APPROVED'
       AND NOT EXISTS (
           SELECT 1 FROM load_distribution_parts p
           WHERE p.distribution_id = OLD.id AND p.status <> 'APPROVED'
       )
       AND EXISTS (
           SELECT 1 FROM load_distribution_parts p JOIN load_plans lp
             ON lp.id = p.load_plan_id JOIN trips t
             ON t.load_plan_id = lp.recalculated_from_id
           WHERE p.distribution_id = OLD.id AND t.status = 'CANCELED'
       )
    THEN RETURN NEW; END IF;
  END IF;

  -- Unchanged OC90 structure and volume immutability checks.
  IF EXISTS (SELECT 1 FROM deliveries e JOIN load_distribution_parts p
             ON p.id = e.distribution_part_id
             WHERE p.distribution_id = identifier)
     OR (TG_OP = 'UPDATE' AND EXISTS (
        SELECT 1 FROM deliveries e JOIN load_distribution_parts p
          ON p.id = e.distribution_part_id
        WHERE p.distribution_id =
          (to_jsonb(OLD)->>'distribution_id')::uuid))
  THEN
    RAISE EXCEPTION 'operational distribution is immutable'
      USING ERRCODE = '23514', CONSTRAINT = 'ck_deliveries__part_context';
  END IF;
  IF TG_TABLE_NAME = 'load_distribution_parts' AND TG_OP <> 'DELETE' THEN
    PERFORM 1 FROM load_plans WHERE id = NEW.load_plan_id FOR UPDATE;
    IF EXISTS (SELECT 1 FROM deliveries e JOIN trips t ON t.id = e.trip_id
               WHERE t.load_plan_id = NEW.load_plan_id) THEN
      RAISE EXCEPTION 'cannot attach an operated plan to a part'
        USING ERRCODE = '23514', CONSTRAINT = 'ck_deliveries__part_context';
    END IF;
  END IF;
  IF TG_TABLE_NAME = 'load_distribution_orders' AND TG_OP <> 'DELETE' THEN
    PERFORM 1 FROM orders WHERE id = NEW.order_id FOR UPDATE;
    IF NEW.active AND EXISTS (SELECT 1 FROM deliveries
                             WHERE order_id = NEW.order_id
                               AND distribution_part_id IS NULL) THEN
      RAISE EXCEPTION 'order already has a legacy delivery'
        USING ERRCODE = '23514', CONSTRAINT = 'ck_deliveries__assignment';
    END IF;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
"""


def upgrade() -> None:
    op.execute(GUARD_SQL)
    legacy = import_module(
        "migrations.versions.20261020_0028_delivery_distribution_parts"
    )
    # Allow approved sibling and replacement legs while one part is
    # INCOMPLETE. The part and plan must still be APPROVED.
    context = legacy.CONTEXT_SQL.replace(
        "CREATE FUNCTION validate_delivery_part_context()",
        "CREATE OR REPLACE FUNCTION validate_delivery_part_context()",
    ).replace(
        "d.status='APPROVED'",
        "d.status IN ('APPROVED','INCOMPLETE')",
    )
    op.execute(context)

    # OC87's deferred coverage/lifecycle validator must also understand an
    # already-operated sibling. Keep ordinary planning invariants unchanged;
    # only an actual delivery in this distribution justifies an exception.
    integrity = import_module("migrations.versions.20261007_0015_load_distributions")
    old_plan_check = "(d.status<>'APPROVED' AND lp.status<>'CALCULATED')"
    new_plan_check = (
        "(d.status<>'APPROVED' AND lp.status<>'CALCULATED' "
        "AND NOT (d.status IN ('INCOMPLETE','PARTIALLY_APPROVED','PROPOSED') "
        "AND p.status IN ('APPROVED','CANCELED') "
        "AND lp.status='APPROVED' AND EXISTS ("
        "SELECT 1 FROM deliveries e WHERE e.distribution_part_id=p.id)))"
    )
    old_order_check = "(d.status<>'APPROVED' AND o.status<>'READY')"
    new_order_check = (
        "(d.status<>'APPROVED' AND o.status<>'READY' "
        "AND NOT (d.status IN ('INCOMPLETE','PARTIALLY_APPROVED','PROPOSED') "
        "AND o.status IN ('PLANNED','IN_TRANSIT','DELIVERED') "
        "AND EXISTS (SELECT 1 FROM deliveries e "
        "JOIN load_distribution_parts p ON p.id=e.distribution_part_id "
        "WHERE p.distribution_id=d.id AND e.order_id=o.id)))"
    )
    source = integrity.INTEGRITY_SQL
    if source.count(old_plan_check) != 1 or source.count(old_order_check) != 1:
        raise RuntimeError("OC94 distribution lifecycle guard drifted")
    guarded = source.replace(old_plan_check, new_plan_check).replace(
        old_order_check, new_order_check
    )
    op.execute(
        guarded.replace(
            "CREATE FUNCTION validate_load_distributions()",
            "CREATE OR REPLACE FUNCTION validate_load_distributions()",
        )
    )


def downgrade() -> None:
    integrity = import_module("migrations.versions.20261007_0015_load_distributions")
    op.execute(
        integrity.INTEGRITY_SQL.replace(
            "CREATE FUNCTION validate_load_distributions()",
            "CREATE OR REPLACE FUNCTION validate_load_distributions()",
        )
    )
    legacy = import_module(
        "migrations.versions.20261020_0028_delivery_distribution_parts"
    )
    context = legacy.CONTEXT_SQL.replace(
        "CREATE FUNCTION validate_delivery_part_context()",
        "CREATE OR REPLACE FUNCTION validate_delivery_part_context()",
    )
    op.execute(context)
    parent = legacy.PARENT_SQL.split("CREATE FUNCTION protect_trip_delivery_plan()")[0]
    op.execute(
        parent.replace(
            "CREATE FUNCTION protect_operational_distribution()",
            "CREATE OR REPLACE FUNCTION protect_operational_distribution()",
        )
    )
