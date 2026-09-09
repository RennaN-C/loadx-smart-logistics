import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.deliveries.models import Delivery, Trip


class DeliveryReferenceService:
    """Public read boundary for modules that reference deliveries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_delivery(self, delivery_id: uuid.UUID) -> Delivery | None:
        return self.db.get(Delivery, delivery_id)

    def get_active_trip_for_driver(self, driver_id: uuid.UUID) -> Trip | None:
        statement = (
            select(Trip)
            .where(
                Trip.driver_id == driver_id,
                Trip.status.in_(("SCHEDULED", "IN_ROUTE")),
            )
            .order_by(Trip.id)
            .limit(2)
        )
        trips = tuple(self.db.scalars(statement))
        return trips[0] if len(trips) == 1 else None

    def get_current_delivery(self, trip_id: uuid.UUID) -> Delivery | None:
        statement = (
            select(Delivery)
            .where(
                Delivery.trip_id == trip_id,
                Delivery.status.in_(("PENDING", "IN_DELIVERY")),
            )
            .order_by(Delivery.sequence, Delivery.id)
            .limit(1)
        )
        return self.db.scalar(statement)
