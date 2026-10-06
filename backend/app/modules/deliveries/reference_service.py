import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.repository import TripRepository


@dataclass(frozen=True, slots=True)
class TripStatusCounts:
    total: int
    scheduled: int
    in_route: int
    finished: int


@dataclass(frozen=True, slots=True)
class DeliveryStatusCounts:
    total: int
    pending: int
    in_delivery: int
    delivered: int


class DeliveryReferenceService:
    """Public read boundary for modules that reference deliveries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_delivery(self, delivery_id: uuid.UUID) -> Delivery | None:
        return self.db.get(Delivery, delivery_id)

    def get_trip_status_counts(self) -> TripStatusCounts:
        counts = TripRepository(self.db).count_trips_by_status()
        return TripStatusCounts(
            total=sum(counts.values()),
            scheduled=counts.get("SCHEDULED", 0),
            in_route=counts.get("IN_ROUTE", 0),
            finished=counts.get("FINISHED", 0),
        )

    def get_delivery_status_counts(self) -> DeliveryStatusCounts:
        counts = TripRepository(self.db).count_deliveries_by_status()
        return DeliveryStatusCounts(
            total=sum(counts.values()),
            pending=counts.get("PENDING", 0),
            in_delivery=counts.get("IN_DELIVERY", 0),
            delivered=counts.get("DELIVERED", 0),
        )

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
