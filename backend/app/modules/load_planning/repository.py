import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.load_planning.models import LoadPlan, LoadPlanItem


class LoadPlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, load_plan_id: uuid.UUID) -> LoadPlan | None:
        statement = (
            select(LoadPlan)
            .options(
                selectinload(LoadPlan.orders),
                selectinload(LoadPlan.items),
                selectinload(LoadPlan.recalculated_from),
            )
            .where(LoadPlan.id == load_plan_id)
        )
        return self.db.scalar(statement)

    def get_for_update(self, load_plan_id: uuid.UUID) -> LoadPlan | None:
        statement = (
            select(LoadPlan)
            .options(
                selectinload(LoadPlan.orders),
                selectinload(LoadPlan.items),
            )
            .where(LoadPlan.id == load_plan_id)
            .with_for_update()
        )
        return self.db.scalar(statement)

    def has_order_item_references(
        self,
        order_item_ids: Sequence[uuid.UUID],
    ) -> bool:
        identifiers = tuple(order_item_ids)
        if not identifiers:
            return False
        statement = (
            select(LoadPlanItem.id)
            .where(LoadPlanItem.order_item_id.in_(identifiers))
            .limit(1)
        )
        return self.db.scalar(statement) is not None

    def add(self, load_plan: LoadPlan) -> LoadPlan:
        items = list(load_plan.items)
        load_plan.items = []
        self.db.add(load_plan)
        self.db.flush()
        load_plan.items = items
        self.db.flush()
        return load_plan

    def update(self, load_plan: LoadPlan) -> LoadPlan:
        self.db.add(load_plan)
        self.db.flush()
        return load_plan
