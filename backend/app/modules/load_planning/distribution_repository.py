import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.load_planning.distribution_models import (
    LoadDistribution,
    LoadDistributionOrder,
    LoadDistributionPart,
    LoadDistributionVolume,
)
from app.modules.load_planning.models import LoadPlan
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID


class LoadDistributionRepository:
    def __init__(
        self, db: Session, organization_id: uuid.UUID = LEGACY_ORGANIZATION_ID
    ) -> None:
        self.db = db
        self.organization_id = organization_id

    def get(
        self, identifier: uuid.UUID, *, for_update: bool = False
    ) -> LoadDistribution | None:
        query = (
            select(LoadDistribution)
            .where(
                LoadDistribution.organization_id == self.organization_id,
                LoadDistribution.id == identifier,
            )
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

    def get_status(self, identifier: uuid.UUID) -> str | None:
        return self.db.scalar(
            select(LoadDistribution.status).where(
                LoadDistribution.organization_id == self.organization_id,
                LoadDistribution.id == identifier,
            )
        )

    def plan_part(self, load_plan_id: uuid.UUID) -> LoadDistributionPart | None:
        # Historical versions remain associated through their descendant chain.
        plan_id = load_plan_id
        seen = set()
        while plan_id is not None and plan_id not in seen:
            seen.add(plan_id)
            part = self.db.scalar(
                select(LoadDistributionPart).where(
                    LoadDistributionPart.organization_id == self.organization_id,
                    LoadDistributionPart.load_plan_id == plan_id,
                )
            )
            if part is not None:
                return part
            plan_id = self.db.scalar(
                select(LoadPlan.id)
                .where(
                    LoadPlan.organization_id == self.organization_id,
                    LoadPlan.recalculated_from_id == plan_id,
                )
                .limit(1)
            )
        return None

    def has_active_orders(self, order_ids: Sequence[uuid.UUID]) -> bool:
        return (
            self.db.scalar(
                select(LoadDistributionOrder.order_id)
                .where(
                    LoadDistributionOrder.organization_id == self.organization_id,
                    LoadDistributionOrder.order_id.in_(order_ids),
                    LoadDistributionOrder.active.is_(True),
                )
                .limit(1)
            )
            is not None
        )

    def order_parts(
        self, part_id: uuid.UUID, order_id: uuid.UUID
    ) -> tuple[uuid.UUID, tuple[uuid.UUID, ...]] | None:
        distribution_id = self.db.scalar(
            select(LoadDistributionPart.distribution_id).where(
                LoadDistributionPart.organization_id == self.organization_id,
                LoadDistributionPart.id == part_id,
            )
        )
        if distribution_id is None:
            return None
        part_ids = tuple(
            self.db.scalars(
                select(LoadDistributionVolume.part_id)
                .where(
                    LoadDistributionVolume.organization_id == self.organization_id,
                    LoadDistributionVolume.distribution_id == distribution_id,
                    LoadDistributionVolume.order_id == order_id,
                )
                .distinct()
                .order_by(LoadDistributionVolume.part_id)
            ).all()
        )
        if part_id not in part_ids:
            return None
        return distribution_id, part_ids

    def add(self, distribution: LoadDistribution) -> None:
        if distribution.organization_id != self.organization_id:
            raise ValueError("Load distribution belongs to a different organization")
        self.db.add(distribution)
        self.db.flush()
