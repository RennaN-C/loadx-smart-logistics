"""Non-mutating preflight for operational cancellation.

The transaction and physical release contract is not approved yet.
"""

import uuid

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.deliveries.service import (
    TripAccessForbiddenError,
    TripNotFoundError,
    TripService,
)
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.users.models import User


class TripCancellationPreflight(BaseModel):
    trip_id: uuid.UUID
    safe_for_cancellation_workflow: bool
    blocking_reasons: list[str]
    next_action: str

    model_config = ConfigDict(extra="forbid")


def assess_cancellation(
    *,
    status: str,
    delivery_statuses: tuple[str, ...],
    has_distribution_part: bool,
    loading_status: str | None,
) -> list[str]:
    """Conservative decisions, no data writes and no synthetic state changes."""
    blockers: list[str] = []
    if status != "SCHEDULED":
        blockers.append("TRIP_ALREADY_STARTED_OR_FINISHED")
    if loading_status is not None:
        # A PENDING loading session already participates in truck reservation.
        blockers.append("LOADING_SESSION_EXISTS")
    # Distribution-specific invariants are rechecked in the POST under locks.
    if not delivery_statuses or any(
        delivery_status != "PENDING" for delivery_status in delivery_statuses
    ):
        blockers.append("DELIVERY_ALREADY_STARTED_OR_MISSING")
    return blockers


class TripCancellationPreflightService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def assess(
        self, trip_id: uuid.UUID, *, current_user: User
    ) -> TripCancellationPreflight:
        trips = TripService(self.db)
        try:
            trip = trips.get_trip(trip_id, current_user=current_user)
        except TripNotFoundError:
            raise ApiError(404, "TRIP_NOT_FOUND", "Viagem nao encontrada.") from None
        except TripAccessForbiddenError:
            raise ApiError(
                403, "AUTH_FORBIDDEN", "Acesso nao autorizado a viagem."
            ) from None

        loading = LoadingReferenceService(self.db).get_by_load_plan_id(
            trip.load_plan_id
        )
        blockers = assess_cancellation(
            status=trip.status,
            delivery_statuses=tuple(row.status for row in trip.deliveries),
            has_distribution_part=any(
                row.distribution_part_id is not None for row in trip.deliveries
            ),
            loading_status=loading.status if loading else None,
        )
        return TripCancellationPreflight(
            trip_id=trip.id,
            safe_for_cancellation_workflow=not blockers,
            blocking_reasons=blockers,
            next_action=(
                "PREPARAR_RECONCILIACAO_TRANSACIONAL"
                if not blockers
                else "RESOLVER_BLOQUEIOS_OPERACIONAIS"
            ),
        )
