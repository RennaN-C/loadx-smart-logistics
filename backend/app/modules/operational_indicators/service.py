from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.occurrences.reference_service import OccurrenceReferenceService
from app.modules.trucks.operational_status_service import TruckOperationalStatusService


@dataclass(frozen=True, slots=True)
class FleetIndicators:
    period: str
    total: int
    active: int
    inactive: int
    available: int
    unavailable: int
    with_operation_conflict: int


@dataclass(frozen=True, slots=True)
class TripIndicators:
    period: str
    total: int
    scheduled: int
    in_route: int
    finished: int


@dataclass(frozen=True, slots=True)
class DeliveryIndicators:
    period: str
    total: int
    pending: int
    in_delivery: int
    delivered: int


@dataclass(frozen=True, slots=True)
class OccurrenceIndicators:
    period: str
    total: int


@dataclass(frozen=True, slots=True)
class OperationalIndicators:
    fleet: FleetIndicators
    trips: TripIndicators
    deliveries: DeliveryIndicators
    occurrences: OccurrenceIndicators


class OperationalIndicatorsService:
    """Consolida indicadores usando somente fronteiras públicas dos módulos."""

    def __init__(
        self,
        db: Session,
        *,
        truck_status_service: TruckOperationalStatusService | None = None,
        delivery_reference_service: DeliveryReferenceService | None = None,
        occurrence_reference_service: OccurrenceReferenceService | None = None,
    ) -> None:
        self.truck_status_service = (
            truck_status_service
            if truck_status_service is not None
            else TruckOperationalStatusService(db)
        )
        self.delivery_reference_service = (
            delivery_reference_service
            if delivery_reference_service is not None
            else DeliveryReferenceService(db)
        )
        self.occurrence_reference_service = (
            occurrence_reference_service
            if occurrence_reference_service is not None
            else OccurrenceReferenceService(db)
        )

    def get_indicators(self) -> OperationalIndicators:
        fleet = self.truck_status_service.get_summary()
        trips = self.delivery_reference_service.get_trip_status_counts()
        deliveries = self.delivery_reference_service.get_delivery_status_counts()
        occurrence_total = self.occurrence_reference_service.count_occurrences()

        return OperationalIndicators(
            fleet=FleetIndicators(
                period="CURRENT_SNAPSHOT",
                total=fleet.total,
                active=fleet.active,
                inactive=fleet.inactive,
                available=fleet.available,
                unavailable=fleet.unavailable,
                with_operation_conflict=fleet.with_operation_conflict,
            ),
            trips=TripIndicators(
                period="ALL_TIME",
                total=trips.total,
                scheduled=trips.scheduled,
                in_route=trips.in_route,
                finished=trips.finished,
            ),
            deliveries=DeliveryIndicators(
                period="ALL_TIME",
                total=deliveries.total,
                pending=deliveries.pending,
                in_delivery=deliveries.in_delivery,
                delivered=deliveries.delivered,
            ),
            occurrences=OccurrenceIndicators(
                period="ALL_TIME",
                total=occurrence_total,
            ),
        )
