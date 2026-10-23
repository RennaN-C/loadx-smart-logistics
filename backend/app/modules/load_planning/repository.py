import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, asc, case, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PageResult, PaginationParams
from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.load_planning.distribution_models import LoadDistributionPart
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.orders.reference_service import OrderReferenceService


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
    distribution_id: uuid.UUID | None = None
    operation: dict[str, object] | None = None


class LoadPlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        pagination: PaginationParams,
        *,
        status: str | None = None,
        truck_id: uuid.UUID | None = None,
        include_operations: bool = False,
        operation_scope: str = "all",
    ) -> PageResult[LoadPlanSummary]:
        filters = []
        if status is not None:
            filters.append(LoadPlan.status == status)
        if truck_id is not None:
            filters.append(LoadPlan.truck_id == truck_id)
        direction = asc if pagination.sort_order == "asc" else desc
        operation = self._operation_projection() if include_operations else None
        base = select(LoadPlan.id).select_from(LoadPlan)
        if operation is not None:
            base = base.join(operation, operation.c.load_plan_id == LoadPlan.id)
            if operation_scope == "completed":
                filters.append(operation.c.operation_status == "COMPLETED")
            elif operation_scope == "ongoing":
                filters.extend(
                    (
                        LoadPlan.status != "REJECTED",
                        operation.c.operation_status.in_(
                            ("NOT_STARTED", "IN_PROGRESS", "PARTIALLY_DELIVERED")
                        ),
                    )
                )
        total = (
            self.db.scalar(
                select(func.count()).select_from(base.where(*filters).subquery())
            )
            or 0
        )
        order_count = (
            select(func.count())
            .select_from(LoadPlanOrder)
            .where(LoadPlanOrder.load_plan_id == LoadPlan.id)
            .correlate(LoadPlan)
            .scalar_subquery()
        )
        # Follow ancestors from each current part; old versions stay discoverable.
        versions = select(
            LoadDistributionPart.load_plan_id.label("plan_id"),
            LoadDistributionPart.distribution_id,
        ).cte("distribution_versions", recursive=True)
        versions = versions.union(
            select(LoadPlan.recalculated_from_id, versions.c.distribution_id)
            .join(versions, LoadPlan.id == versions.c.plan_id)
            .where(LoadPlan.recalculated_from_id.is_not(None))
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
                versions.c.distribution_id,
            )
            .outerjoin(versions, versions.c.plan_id == LoadPlan.id)
            .where(*filters)
            .order_by(direction(LoadPlan.created_at), direction(LoadPlan.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        if operation is not None:
            statement = statement.join(
                operation, operation.c.load_plan_id == LoadPlan.id
            ).add_columns(*[c for c in operation.c if c.key != "load_plan_id"])
        items = []
        for row in self.db.execute(statement).mappings():
            values = dict(row)
            if operation is not None:
                summary = {
                    c.key: values.pop(c.key)
                    for c in operation.c
                    if c.key != "load_plan_id"
                }
                summary["status"] = summary.pop("operation_status")
                summary["order_count"] = summary.pop("operation_order_count")
                values["operation"] = summary
            items.append(LoadPlanSummary(**values))
        return PageResult.create(items, pagination, total)

    def get_operation_summary(self, plan_id: uuid.UUID) -> dict[str, object] | None:
        projection = self._operation_projection()
        row = (
            self.db.execute(
                select(projection).where(projection.c.load_plan_id == plan_id)
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        summary = dict(row)
        summary.pop("load_plan_id")
        summary["status"] = summary.pop("operation_status")
        summary["order_count"] = summary.pop("operation_order_count")
        return summary

    @staticmethod
    def _operation_projection():
        orders = OrderReferenceService.planning_status_projection()
        counts = (
            select(
                LoadPlanOrder.load_plan_id,
                func.count().label("operation_order_count"),
                func.count()
                .filter(orders.c.status == "DELIVERED")
                .label("delivered_order_count"),
                func.count()
                .filter(
                    and_(orders.c.status != "DELIVERED", orders.c.has_delivered_leg)
                )
                .label("partial_order_count"),
                func.count()
                .filter(orders.c.status == "READY")
                .label("ready_order_count"),
            )
            .join(orders, orders.c.order_id == LoadPlanOrder.order_id)
            .group_by(LoadPlanOrder.load_plan_id)
            .subquery()
        )
        trip = DeliveryReferenceService.plan_operation_projection()
        loading = LoadingReferenceService.plan_operation_projection()
        state = case(
            (trip.c.trip_status == "CANCELED", "CANCELED"),
            (
                and_(
                    trip.c.trip_status == "FINISHED",
                    counts.c.operation_order_count > 0,
                    counts.c.delivered_order_count == counts.c.operation_order_count,
                ),
                "COMPLETED",
            ),
            (
                and_(
                    trip.c.trip_id.is_not(None),
                    or_(
                        counts.c.partial_order_count > 0,
                        and_(
                            counts.c.delivered_order_count > 0,
                            counts.c.delivered_order_count
                            < counts.c.operation_order_count,
                        ),
                    ),
                ),
                "PARTIALLY_DELIVERED",
            ),
            (
                or_(
                    trip.c.trip_id.is_not(None),
                    loading.c.loading_session_id.is_not(None),
                ),
                "IN_PROGRESS",
            ),
            else_="NOT_STARTED",
        )
        return (
            select(
                LoadPlan.id.label("load_plan_id"),
                state.label("operation_status"),
                loading.c.loading_session_id,
                loading.c.loading_status,
                trip.c.trip_id,
                trip.c.trip_status,
                *[
                    func.coalesce(counts.c[name], 0).label(name)
                    for name in (
                        "operation_order_count",
                        "delivered_order_count",
                        "partial_order_count",
                        "ready_order_count",
                    )
                ],
                func.coalesce(trip.c.delivery_count, 0).label("delivery_count"),
                func.coalesce(trip.c.delivered_leg_count, 0).label(
                    "delivered_leg_count"
                ),
            )
            .select_from(LoadPlan)
            .outerjoin(counts, counts.c.load_plan_id == LoadPlan.id)
            .outerjoin(trip, trip.c.load_plan_id == LoadPlan.id)
            .outerjoin(loading, loading.c.load_plan_id == LoadPlan.id)
            .subquery()
        )

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
            .execution_options(populate_existing=True)
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
