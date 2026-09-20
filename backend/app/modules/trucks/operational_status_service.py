import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.fleet.service import FleetAvailabilityService
from app.modules.trucks.service import TruckService


@dataclass(frozen=True, slots=True)
class TruckOperationalStatus:
    id: uuid.UUID
    plate: str
    model: str
    active: bool
    has_operation_conflict: bool
    available: bool


class TruckOperationalStatusService:
    """Expõe a visão operacional dos caminhões consumindo a fronteira da OC67."""

    def __init__(
        self,
        db: Session,
        *,
        truck_service: TruckService | None = None,
        fleet_service: FleetAvailabilityService | None = None,
    ) -> None:
        self.truck_service = (
            truck_service if truck_service is not None else TruckService(db)
        )
        self.fleet_service = (
            fleet_service if fleet_service is not None else FleetAvailabilityService(db)
        )

    def list_statuses(
        self,
        pagination: PaginationParams,
    ) -> PageResult[TruckOperationalStatus]:
        trucks = self.truck_service.list_trucks(pagination)

        items = tuple(
            self._build_status(truck.id, truck.plate, truck.model)
            for truck in trucks.items
        )

        return PageResult(
            items=items,
            page=trucks.page,
            page_size=trucks.page_size,
            total=trucks.total,
            total_pages=trucks.total_pages,
        )

    def _build_status(
        self,
        truck_id: uuid.UUID,
        plate: str,
        model: str,
    ) -> TruckOperationalStatus:
        availability = self.fleet_service.get_truck_availability(truck_id)

        return TruckOperationalStatus(
            id=truck_id,
            plate=plate,
            model=model,
            active=availability.active,
            has_operation_conflict=availability.has_operation_conflict,
            available=availability.available,
        )
