import uuid

from sqlalchemy.orm import Session

from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.deliveries.service import (
    TripAccessForbiddenError,
    TripNotFoundError,
    TripService,
)
from app.modules.occurrences.models import Occurrence
from app.modules.occurrences.repository import OccurrenceRepository
from app.modules.occurrences.schemas import OccurrenceCreate
from app.modules.users.models import User


class OccurrenceTripNotFoundError(Exception):
    pass


class OccurrenceDeliveryNotFoundError(Exception):
    pass


class OccurrenceDeliveryTripMismatchError(Exception):
    pass


class OccurrenceAccessForbiddenError(Exception):
    pass


class OccurrenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OccurrenceRepository(db)
        self.trip_service = TripService(db)
        self.delivery_reference_service = DeliveryReferenceService(db)

    def register_occurrence(
        self, data: OccurrenceCreate, *, current_user: User
    ) -> Occurrence:
        try:
            self.trip_service.get_trip(data.trip_id, current_user=current_user)
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
            self.db.commit()
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
