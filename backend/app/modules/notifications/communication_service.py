import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResponse, PaginationParams, to_page_response
from app.modules.access_profiles.catalog import Permission, has_permission
from app.modules.deliveries.service import (
    DeliveryNotFoundError,
    TripAccessForbiddenError,
    TripNotFoundError,
    TripService,
)
from app.modules.notifications.communication_repository import (
    DeliveryCommunicationRepository,
)
from app.modules.notifications.communication_schemas import DeliveryCommunicationRead
from app.modules.occurrences.reference_service import OccurrenceReferenceService
from app.modules.users.models import User


class DeliveryCommunicationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DeliveryCommunicationRepository(db)

    def list_for_delivery(
        self, delivery_id: uuid.UUID, user: User, pagination: PaginationParams
    ) -> PageResponse[DeliveryCommunicationRead]:
        if not (
            has_permission(user, Permission.OCCURRENCES_READ)
            or has_permission(user, Permission.TRIPS_OWN)
        ):
            raise ApiError(
                403, "AUTH_FORBIDDEN", "Usuário sem permissão para esta ação."
            )
        try:
            delivery = TripService(self.db).get_delivery_for_access(
                delivery_id, current_user=user
            )
        except TripAccessForbiddenError:
            raise ApiError(
                403, "AUTH_FORBIDDEN", "Usuário sem permissão para esta ação."
            ) from None
        except (DeliveryNotFoundError, TripNotFoundError):
            raise ApiError(
                404, "DELIVERY_NOT_FOUND", "Entrega não encontrada."
            ) from None
        origins = OccurrenceReferenceService(self.db).ids_for_delivery(
            delivery.id, delivery.trip_id
        )
        result = self.repository.page(delivery.trip_id, origins, pagination)
        return to_page_response(
            result,
            (
                DeliveryCommunicationRead.model_validate(dict(row))
                for row in result.items
            ),
        )
