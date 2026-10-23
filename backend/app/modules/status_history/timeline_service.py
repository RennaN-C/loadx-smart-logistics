"""Timeline directly projected from original history and occurrences."""

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.deliveries.cancellation_service import TripCancellation
from app.modules.deliveries.exception_models import DeliveryException
from app.modules.deliveries.interruption_service import TripInterruptionEvent
from app.modules.deliveries.service import TripService
from app.modules.occurrences.models import Occurrence
from app.modules.status_history.models import StatusHistory
from app.modules.status_history.timeline_schemas import (
    TimelineEventRead,
    TimelinePage,
    order_unique_events,
)
from app.modules.users.models import User

MAX_EVENTS_PER_TRIP = 3000


class OperationalTimelineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripService(db)

    def list_trip(
        self,
        trip_id: uuid.UUID,
        *,
        current_user: User,
        page: int,
        page_size: int,
    ) -> TimelinePage:
        trip = self.trips.get_trip(trip_id, current_user=current_user)
        delivery_ids = [delivery.id for delivery in trip.deliveries]
        history = self.db.scalars(
            select(StatusHistory)
            .where(
                or_(
                    and_(
                        StatusHistory.entity_type == "TRIP",
                        StatusHistory.entity_id == trip.id,
                    ),
                    and_(
                        StatusHistory.entity_type == "DELIVERY",
                        StatusHistory.entity_id.in_(delivery_ids),
                    ),
                )
            )
            .order_by(StatusHistory.created_at, StatusHistory.id)
            .limit(MAX_EVENTS_PER_TRIP + 1)
        ).all()
        occurrences = self.db.scalars(
            select(Occurrence)
            .where(Occurrence.trip_id == trip.id)
            .order_by(Occurrence.created_at, Occurrence.id)
            .limit(MAX_EVENTS_PER_TRIP + 1)
        ).all()
        delivery_exceptions = self.db.scalars(
            select(DeliveryException)
            .where(DeliveryException.trip_id == trip.id)
            .order_by(DeliveryException.created_at, DeliveryException.id)
            .limit(MAX_EVENTS_PER_TRIP + 1)
        ).all()
        cancellations = self.db.scalars(
            select(TripCancellation)
            .where(TripCancellation.trip_id == trip.id)
            .order_by(TripCancellation.created_at, TripCancellation.id)
            .limit(MAX_EVENTS_PER_TRIP + 1)
        ).all()
        interruptions = self.db.scalars(
            select(TripInterruptionEvent)
            .where(TripInterruptionEvent.trip_id == trip.id)
            .order_by(TripInterruptionEvent.created_at, TripInterruptionEvent.id)
            .limit(MAX_EVENTS_PER_TRIP + 1)
        ).all()
        if (
            len(history)
            + len(occurrences)
            + len(delivery_exceptions)
            + len(cancellations)
            + len(interruptions)
            > MAX_EVENTS_PER_TRIP
        ):
            raise ApiError(
                409,
                "TIMELINE_TOO_LARGE",
                "Historico muito extenso; consulta agregada precisa de cursor.",
            )

        events = [
            TimelineEventRead(
                id=row.id,
                source="STATUS_HISTORY",
                kind="STATUS_CHANGED",
                entity_id=row.entity_id,
                occurred_at=row.created_at,
                actor_id=row.changed_by,
                status_before=row.old_status,
                status_after=row.new_status,
            )
            for row in history
        ]
        events.extend(
            TimelineEventRead(
                id=row.id,
                source="OCCURRENCE",
                kind=row.type,
                entity_id=row.delivery_id or trip.id,
                occurred_at=row.created_at,
            )
            for row in occurrences
        )
        events.extend(
            TimelineEventRead(
                id=row.id,
                source="DELIVERY_EXCEPTION",
                kind=row.code,
                entity_id=row.delivery_id,
                occurred_at=row.created_at,
                actor_id=row.actor_id,
            )
            for row in delivery_exceptions
        )
        events.extend(
            TimelineEventRead(
                id=row.id,
                source="TRIP_CANCELLATION",
                kind="TRIP_CANCELED",
                entity_id=trip.id,
                occurred_at=row.created_at,
                actor_id=row.actor_id,
            )
            for row in cancellations
        )
        events.extend(
            TimelineEventRead(
                id=row.id,
                source="TRIP_INTERRUPTION",
                kind=row.action,
                entity_id=trip.id,
                occurred_at=row.created_at,
                actor_id=row.actor_id,
            )
            for row in interruptions
        )
        ordered = order_unique_events(events)
        start = (page - 1) * page_size
        return TimelinePage(
            items=ordered[start : start + page_size],
            total=len(ordered),
            page=page,
            page_size=page_size,
        )
