import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PageResult, PaginationParams
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder


@dataclass(frozen=True, slots=True)
class LoadPlanSummary:
    id: uuid.UUID
    truck_id: uuid.UUID
    truck_plate: str
    truck_model: str
    status: str
    created_at: datetime
    recalculated_from_id: uuid.UUID | None
    loaded_count: int
    unloaded_count: int
    occupancy_percent: Decimal
    total_weight_kg: Decimal
    order_count: int


class LoadPlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        pagination: PaginationParams,
        *,
        status: str | None = None,
        truck_id: uuid.UUID | None = None,
    ) -> PageResult[LoadPlanSummary]:
        filters = []
        if status is not None:
            filters.append(LoadPlan.status == status)
        if truck_id is not None:
            filters.append(LoadPlan.truck_id == truck_id)
        direction = asc if pagination.sort_order == "asc" else desc
        total = (
            self.db.scalar(select(func.count()).select_from(LoadPlan).where(*filters))
            or 0
        )
        order_count = (
            select(func.count())
            .select_from(LoadPlanOrder)
            .where(LoadPlanOrder.load_plan_id == LoadPlan.id)
            .correlate(LoadPlan)
            .scalar_subquery()
        )
        statement = (
            select(
                LoadPlan.id,
                LoadPlan.truck_id,
                LoadPlan.truck_snapshot_plate.label("truck_plate"),
                LoadPlan.truck_snapshot_model.label("truck_model"),
                LoadPlan.status,
                LoadPlan.created_at,
                LoadPlan.recalculated_from_id,
                LoadPlan.loaded_count,
                LoadPlan.unloaded_count,
                LoadPlan.occupancy_percent,
                LoadPlan.total_weight_kg,
                order_count.label("order_count"),
            )
            .where(*filters)
            .order_by(direction(LoadPlan.created_at), direction(LoadPlan.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        items = [
            LoadPlanSummary(**dict(row))
            for row in self.db.execute(statement).mappings()
        ]
        return PageResult.create(items, pagination, total)

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
