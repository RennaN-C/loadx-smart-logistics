import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.pagination import PageResult, PaginationParams
from app.modules.deliveries.models import Delivery, Trip


@dataclass(frozen=True, slots=True)
class TripListItem:
    trip: Trip
    delivery_count: int


class TripRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, trip_id: uuid.UUID) -> Trip | None:
        statement = (
            select(Trip)
            .options(selectinload(Trip.deliveries))
            .where(Trip.id == trip_id)
        )
        return self.db.scalar(statement)

    def list(
        self,
        pagination: PaginationParams,
        *,
        driver_id: uuid.UUID | None = None,
    ) -> PageResult[TripListItem]:
        direction = asc if pagination.sort_order == "asc" else desc
        filters = (Trip.driver_id == driver_id,) if driver_id is not None else ()
        total = (
            self.db.scalar(select(func.count()).select_from(Trip).where(*filters)) or 0
        )
        delivery_count = (
            select(func.count(Delivery.id))
            .where(Delivery.trip_id == Trip.id)
            .correlate(Trip)
            .scalar_subquery()
        )
        statement = (
            select(Trip, delivery_count.label("delivery_count"))
            .where(*filters)
            .order_by(direction(Trip.created_at), direction(Trip.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        items = tuple(
            TripListItem(trip=trip, delivery_count=delivery_total)
            for trip, delivery_total in self.db.execute(statement).all()
        )
        return PageResult.create(items, pagination, total)

    def get_for_update(self, trip_id: uuid.UUID) -> Trip | None:
        statement = select(Trip).where(Trip.id == trip_id).with_for_update()
        return self.db.scalar(statement)

    def list_deliveries_for_update(self, trip_id: uuid.UUID) -> Sequence[Delivery]:
        statement = (
            select(Delivery)
            .where(Delivery.trip_id == trip_id)
            .order_by(Delivery.id.asc())
            .with_for_update()
        )
        return self.db.scalars(statement).all()

    def get_delivery(self, delivery_id: uuid.UUID) -> Delivery | None:
        return self.db.get(Delivery, delivery_id)

    def get_delivery_for_update(self, delivery_id: uuid.UUID) -> Delivery | None:
        statement = select(Delivery).where(Delivery.id == delivery_id).with_for_update()
        return self.db.scalar(statement)

    def get_by_load_plan_id(self, load_plan_id: uuid.UUID) -> Trip | None:
        statement = select(Trip).where(Trip.load_plan_id == load_plan_id)
        return self.db.scalar(statement)

    def assigned_order_ids(
        self,
        order_ids: Sequence[uuid.UUID],
    ) -> frozenset[uuid.UUID]:
        identifiers = tuple(order_ids)
        if not identifiers:
            return frozenset()
        statement = select(Delivery.order_id).where(Delivery.order_id.in_(identifiers))
        return frozenset(self.db.scalars(statement).all())

    def add(self, trip: Trip) -> Trip:
        self.db.add(trip)
        self.db.flush()
        return trip

    def update_trip(self, trip: Trip) -> Trip:
        self.db.add(trip)
        self.db.flush()
        return trip

    def update_delivery(self, delivery: Delivery) -> Delivery:
        self.db.add(delivery)
        self.db.flush()
        return delivery
