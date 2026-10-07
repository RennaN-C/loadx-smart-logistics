import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.load_planning.distribution_models import (
    LoadDistribution,
    LoadDistributionOrder,
    LoadDistributionPart,
)
from app.modules.load_planning.models import LoadPlan


class LoadDistributionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(
        self, identifier: uuid.UUID, *, for_update: bool = False
    ) -> LoadDistribution | None:
        query = (
            select(LoadDistribution)
            .where(LoadDistribution.id == identifier)
            .options(
                selectinload(LoadDistribution.orders),
                selectinload(LoadDistribution.parts),
                selectinload(LoadDistribution.volumes),
            )
            .execution_options(populate_existing=True)
        )
        if for_update:
            query = query.with_for_update()
        return self.db.scalar(query)

    def plan_part(self, load_plan_id: uuid.UUID) -> LoadDistributionPart | None:
        # Historical versions remain associated through their descendant chain.
        plan_id = load_plan_id
        seen = set()
        while plan_id is not None and plan_id not in seen:
            seen.add(plan_id)
            part = self.db.scalar(
                select(LoadDistributionPart).where(
                    LoadDistributionPart.load_plan_id == plan_id
                )
            )
            if part is not None:
                return part
            plan_id = self.db.scalar(
                select(LoadPlan.id)
                .where(LoadPlan.recalculated_from_id == plan_id)
                .limit(1)
            )
        return None

    def has_active_orders(self, order_ids: Sequence[uuid.UUID]) -> bool:
        return (
            self.db.scalar(
                select(LoadDistributionOrder.order_id)
                .where(
                    LoadDistributionOrder.order_id.in_(order_ids),
                    LoadDistributionOrder.active.is_(True),
                )
                .limit(1)
            )
            is not None
        )

    def add(self, distribution: LoadDistribution) -> None:
        self.db.add(distribution)
        self.db.flush()
