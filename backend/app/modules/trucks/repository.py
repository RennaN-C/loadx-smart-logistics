import uuid
from collections.abc import Sequence

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.deliveries.models import Trip
from app.modules.load_planning.models import LoadPlan
from app.modules.loading.models import LoadingSession
from app.modules.trucks.models import Truck


class TruckRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, pagination: PaginationParams) -> PageResult[Truck]:
        direction = asc if pagination.sort_order == "asc" else desc
        total = self.db.scalar(select(func.count()).select_from(Truck)) or 0
        statement = (
            select(Truck)
            .order_by(direction(Truck.created_at), direction(Truck.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return PageResult.create(
            self.db.scalars(statement).all(),
            pagination,
            total,
        )

    def get(self, truck_id: uuid.UUID) -> Truck | None:
        return self.db.get(Truck, truck_id)

    def get_many(self, truck_ids: Sequence[uuid.UUID]) -> Sequence[Truck]:
        unique_ids = tuple(sorted(set(truck_ids), key=lambda value: value.int))
        if not unique_ids:
            return ()
        statement = (
            select(Truck).where(Truck.id.in_(unique_ids)).order_by(Truck.id.asc())
        )
        return self.db.scalars(statement).all()

    def get_for_update(self, truck_id: uuid.UUID) -> Truck | None:
        statement = select(Truck).where(Truck.id == truck_id).with_for_update()
        return self.db.scalar(statement)

    def has_operation_conflict(
        self,
        truck_id: uuid.UUID,
        *,
        exclude_load_plan_id: uuid.UUID | None = None,
    ) -> bool:
        filters = [LoadPlan.truck_id == truck_id]
        if exclude_load_plan_id is not None:
            filters.append(LoadPlan.id != exclude_load_plan_id)

        active_operation = or_(
            and_(
                LoadingSession.id.is_not(None),
                or_(
                    Trip.id.is_(None),
                    Trip.status != "FINISHED",
                ),
            ),
            Trip.status.in_(("SCHEDULED", "IN_ROUTE")),
        )

        statement = (
            select(LoadPlan.id)
            .outerjoin(
                LoadingSession,
                LoadingSession.load_plan_id == LoadPlan.id,
            )
            .outerjoin(
                Trip,
                Trip.load_plan_id == LoadPlan.id,
            )
            .where(*filters, active_operation)
            .limit(1)
        )
        return self.db.scalar(statement) is not None

    def get_by_plate(self, plate: str) -> Truck | None:
        statement = select(Truck).where(Truck.plate == plate)
        return self.db.scalar(statement)

    def add(self, truck: Truck) -> Truck:
        self.db.add(truck)
        self.db.flush()
        self.db.refresh(truck)
        return truck

    def update(self, truck: Truck) -> Truck:
        self.db.add(truck)
        self.db.flush()
        self.db.refresh(truck)
        return truck
