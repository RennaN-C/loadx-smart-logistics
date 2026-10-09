import uuid
from datetime import datetime

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.trucks.models import TruckMaintenance


class MaintenanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self, truck_id: uuid.UUID, pagination: PaginationParams
    ) -> PageResult[TruckMaintenance]:
        filters = (TruckMaintenance.truck_id == truck_id,)
        direction = asc if pagination.sort_order == "asc" else desc
        total = (
            self.db.scalar(
                select(func.count()).select_from(TruckMaintenance).where(*filters)
            )
            or 0
        )
        rows = self.db.scalars(
            select(TruckMaintenance)
            .where(*filters)
            .order_by(
                direction(TruckMaintenance.starts_at), direction(TruckMaintenance.id)
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
        return PageResult.create(rows, pagination, total)

    def get_for_update(
        self, truck_id: uuid.UUID, identifier: uuid.UUID
    ) -> TruckMaintenance | None:
        return self.db.scalar(
            select(TruckMaintenance)
            .where(
                TruckMaintenance.truck_id == truck_id, TruckMaintenance.id == identifier
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def has_block(self, truck_id: uuid.UUID, at: datetime) -> bool:
        query = (
            select(TruckMaintenance.id)
            .where(
                TruckMaintenance.truck_id == truck_id,
                TruckMaintenance.closed_at.is_(None),
                TruckMaintenance.starts_at <= at,
                or_(TruckMaintenance.ends_at.is_(None), TruckMaintenance.ends_at > at),
            )
            .limit(1)
        )
        return self.db.scalar(query) is not None

    def save(self, record: TruckMaintenance) -> TruckMaintenance:
        self.db.add(record)
        self.db.flush()
        return record
