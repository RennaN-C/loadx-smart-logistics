import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Select, func, select
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

    @staticmethod
    def plan_operation_projection():
        """Composable public projection; no recipient or driver personal data."""
        legs = (
            select(
                Delivery.trip_id,
                func.count().label("delivery_count"),
                func.count()
                .filter(Delivery.status == "DELIVERED")
                .label("delivered_leg_count"),
            )
            .group_by(Delivery.trip_id)
            .subquery()
        )
        return (
            select(
                Trip.load_plan_id,
                Trip.id.label("trip_id"),
                Trip.status.label("trip_status"),
                func.coalesce(legs.c.delivery_count, 0).label("delivery_count"),
                func.coalesce(legs.c.delivered_leg_count, 0).label(
                    "delivered_leg_count"
                ),
            )
            .outerjoin(legs, legs.c.trip_id == Trip.id)
            .subquery()
        )

    @staticmethod
    def delivered_order_ids():
        """Orders with any delivered leg; this does not mean fully delivered."""
        return select(Delivery.order_id).where(Delivery.status == "DELIVERED")

    def trip_ids_for_driver(self, driver_id: uuid.UUID) -> Select[tuple[uuid.UUID]]:
        """Composable ownership scope; callers must also validate the active identity."""
        return TripRepository(self.db).ids_for_driver(driver_id)

    def get_trip_for_notification(self, trip_id: uuid.UUID) -> Trip | None:
        """Lock the current operational recipient during notification processing."""
        return TripRepository(self.db).get_for_update(trip_id)

    def get_trip_for_load_plan(self, load_plan_id: uuid.UUID) -> Trip | None:
        """Exact lookup, including finished trips; never scans the global list."""
        return TripRepository(self.db).get_by_load_plan_id(load_plan_id)

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
            statuses=("SCHEDULED", "IN_ROUTE", "INTERRUPTED"),
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
