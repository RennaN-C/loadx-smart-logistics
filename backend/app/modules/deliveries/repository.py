import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.deliveries.models import Delivery, Trip


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
