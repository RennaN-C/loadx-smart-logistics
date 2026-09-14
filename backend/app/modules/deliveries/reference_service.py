import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.repository import TripRepository


class DeliveryReferenceService:
    """Public read boundary for modules that reference deliveries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_delivery(self, delivery_id: uuid.UUID) -> Delivery | None:
        return self.db.get(Delivery, delivery_id)

    def get_active_trip_for_driver(self, driver_id: uuid.UUID) -> Trip | None:
        trips = self.list_active_trips_for_driver(driver_id)
        return trips[0] if len(trips) == 1 else None

    def list_active_trips_for_driver(
        self,
        driver_id: uuid.UUID,
        *,
        exclude_trip_id: uuid.UUID | None = None,
    ) -> Sequence[Trip]:
        """Return at most two trips; two also signal ambiguous legacy allocation."""
        return TripRepository(self.db).list_driver_trips(
            driver_id,
            statuses=("SCHEDULED", "IN_ROUTE"),
            exclude_trip_id=exclude_trip_id,
        )

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
