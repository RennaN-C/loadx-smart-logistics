import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.load_planning.distribution_repository import LoadDistributionRepository
from app.modules.load_planning.repository import LoadPlanRepository


@dataclass(frozen=True, slots=True)
class OperationalLoadPlan:
    id: uuid.UUID
    truck_id: uuid.UUID
    status: str
    order_ids: tuple[uuid.UUID, ...]
    operational_ready: bool = True


@dataclass(frozen=True, slots=True)
class LoadingPlanItemReference:
    id: uuid.UUID
    loading_sequence: int


class LoadPlanReferenceService:
    """Public cross-module queries owned by load planning."""

    def __init__(self, db: Session) -> None:
        self.repository = LoadPlanRepository(db)
        self.distributions = LoadDistributionRepository(db)

    def has_order_item_references(
        self,
        order_item_ids: Sequence[uuid.UUID],
    ) -> bool:
        return self.repository.has_order_item_references(order_item_ids)

    def has_active_distribution_orders(self, order_ids: Sequence[uuid.UUID]) -> bool:
        return self.distributions.has_active_orders(order_ids)

    def get_operational_plan(
        self,
        load_plan_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> OperationalLoadPlan | None:
        load_plan = (
            self.repository.get_for_update(load_plan_id)
            if for_update
            else self.repository.get(load_plan_id)
        )
        if load_plan is None:
            return None
        part = self.distributions.plan_part(load_plan_id)
        operational_ready = True
        if part is not None:
            distribution = self.distributions.get(part.distribution_id)
            operational_ready = (
                distribution.status == "APPROVED"
                and len(distribution.parts) == 1
                and part.load_plan_id == load_plan_id
            )
        return OperationalLoadPlan(
            id=load_plan.id,
            truck_id=load_plan.truck_id,
            status=load_plan.status,
            order_ids=tuple(link.order_id for link in load_plan.orders),
            operational_ready=operational_ready,
        )

    def get_loading_items(
        self,
        load_plan_id: uuid.UUID,
    ) -> tuple[LoadingPlanItemReference, ...]:
        load_plan = self.repository.get(load_plan_id)
        if load_plan is None or load_plan.status != "APPROVED":
            return ()
        return tuple(
            LoadingPlanItemReference(item.id, item.loading_sequence)
            for item in sorted(
                load_plan.items,
                key=lambda item: item.loading_sequence or 0,
            )
            if item.placed and item.loading_sequence is not None
        )
