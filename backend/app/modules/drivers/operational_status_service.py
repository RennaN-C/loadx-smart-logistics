import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.drivers.models import Driver
from app.modules.drivers.service import DriverService
from app.modules.fleet.service import FleetAvailabilityService


@dataclass(frozen=True, slots=True)
class DriverOperationalStatus:
    id: uuid.UUID
    name: str
    license_category: str | null
    active: bool
    has_operation_conflict: bool
    available: bool


class DriverOperationalStatusService:
    """Expõe a situação operacional dos motoristas usando a fronteira da OC67."""

    def __init__(
        self,
        db: Session,
        *,
        driver_service: DriverService | None = None,
        fleet_service: FleetAvailabilityService | None = None,
    ) -> None:
        self.driver_service = (
            driver_service if driver_service is not None else DriverService(db)
        )
        self.fleet_service = (
            fleet_service if fleet_service is not None else FleetAvailabilityService(db)
        )

    def list_statuses(
        self,
        pagination: PaginationParams,
    ) -> PageResult[DriverOperationalStatus]:
        drivers = self.driver_service.list_drivers(pagination)

        items = tuple(self._build_status(driver) for driver in drivers.items)

        return PageResult(
            items=items,
            page=drivers.page,
            page_size=drivers.page_size,
            total=drivers.total,
            total_pages=drivers.total_pages,
        )

    def _build_status(self, driver: Driver) -> DriverOperationalStatus:
        availability = self.fleet_service.get_driver_availability(driver.id)

        return DriverOperationalStatus(
            id=driver.id,
            name=driver.name,
            license_category=driver.license_category,
            active=availability.active,
            has_operation_conflict=availability.has_operation_conflict,
            available=availability.available,
        )
