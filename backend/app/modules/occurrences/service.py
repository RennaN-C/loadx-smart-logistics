import uuid

from sqlalchemy.orm import Session

from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.deliveries.service import (
    TripAccessForbiddenError,
    TripNotFoundError,
    TripService,
)
from app.modules.drivers.service import DriverService
from app.modules.notifications.service import OperationalNotificationService
from app.modules.occurrences.models import Occurrence
from app.modules.occurrences.repository import OccurrenceRepository
from app.modules.occurrences.schemas import OccurrenceCreate
from app.modules.users.models import User


class OccurrenceNotFoundError(Exception):
    pass


class OccurrenceTripNotFoundError(Exception):
    pass


class OccurrenceDeliveryNotFoundError(Exception):
    pass


class OccurrenceDeliveryTripMismatchError(Exception):
    pass


class OccurrenceAccessForbiddenError(Exception):
    pass


class OccurrenceService:
    def __init__(
        self,
        db: Session,
        *,
        notification_service: OperationalNotificationService | None = None,
    ) -> None:
        self.db = db
        self.repository = OccurrenceRepository(db)
        self.trip_service = TripService(db)
        self.delivery_reference_service = DeliveryReferenceService(db)
        self.driver_service = DriverService(db)
        self.notification_service = (
            notification_service or OperationalNotificationService()
        )

    def get_occurrence_for_access(
        self, occurrence_id: uuid.UUID, *, current_user: User
    ) -> Occurrence:
        occurrence = self.repository.get(occurrence_id)
        if occurrence is None:
            raise OccurrenceNotFoundError
        self.trip_service.get_trip(occurrence.trip_id, current_user=current_user)
        return occurrence

    def register_occurrence(
        self, data: OccurrenceCreate, *, current_user: User
    ) -> Occurrence:
        try:
            trip = self.trip_service.get_trip(
                data.trip_id, current_user=current_user, for_update=True
            )
        except TripNotFoundError as exc:
            raise OccurrenceTripNotFoundError from exc
        except TripAccessForbiddenError as exc:
            raise OccurrenceAccessForbiddenError from exc

        if data.delivery_id is not None:
            delivery = self.delivery_reference_service.get_delivery(data.delivery_id)
            if delivery is None:
                raise OccurrenceDeliveryNotFoundError
            if delivery.trip_id != data.trip_id:
                raise OccurrenceDeliveryTripMismatchError

        occurrence = Occurrence(**data.model_dump())
        try:
            occurrence = self.repository.add(occurrence)
            self.notification_service.stage(
                self.db,
                event_type="OCCURRENCE_REGISTERED",
                trip_id=trip.id,
                recipient_driver_id=trip.driver_id,
                occurrence_id=occurrence.id,
            )
            self.db.commit()
            OperationalNotificationService.dispatch_after_commit(self.db)
            self.db.refresh(occurrence)
            return occurrence
        except Exception:
            self.db.rollback()
            raise

    def list_trip_occurrences(
        self,
        trip_id: uuid.UUID,
        *,
        current_user: User,
    ) -> list[Occurrence]:
        try:
            self.trip_service.get_trip(trip_id, current_user=current_user)
        except TripNotFoundError as exc:
            raise OccurrenceTripNotFoundError from exc
        except TripAccessForbiddenError as exc:
            raise OccurrenceAccessForbiddenError from exc
        return self.repository.list_by_trip_id(trip_id)
