import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.drivers.service import DriverService
from app.modules.trucks.service import TruckService


@dataclass(frozen=True, slots=True)
class TruckAvailability:
    truck_id: uuid.UUID
    active: bool
    has_operation_conflict: bool
    available: bool


@dataclass(frozen=True, slots=True)
class DriverAvailability:
    driver_id: uuid.UUID
    active: bool
    has_operation_conflict: bool
    available: bool


@dataclass(frozen=True, slots=True)
class OperationAvailability:
    truck: TruckAvailability
    driver: DriverAvailability
    available: bool


class FleetAvailabilityService:
    """Consolida disponibilidade operacional sem duplicar regras de conflito."""

    def __init__(
        self,
        db: Session,
        *,
        truck_service: TruckService | None = None,
        driver_service: DriverService | None = None,
    ) -> None:
        self.truck_service = (
            truck_service if truck_service is not None else TruckService(db)
        )
        self.driver_service = (
            driver_service if driver_service is not None else DriverService(db)
        )

    def get_truck_availability(
        self,
        truck_id: uuid.UUID,
    ) -> TruckAvailability:
        truck = self.truck_service.get_truck(truck_id)
        has_conflict = self.truck_service.has_operation_conflict(truck_id)

        return TruckAvailability(
            truck_id=truck.id,
            active=truck.active,
            has_operation_conflict=has_conflict,
            available=truck.active and not has_conflict,
        )

    def get_driver_availability(
        self,
        driver_id: uuid.UUID,
    ) -> DriverAvailability:
        driver = self.driver_service.get_driver(driver_id)
        has_conflict = self.driver_service.has_operation_conflict(driver_id)

        return DriverAvailability(
            driver_id=driver.id,
            active=driver.active,
            has_operation_conflict=has_conflict,
            available=driver.active and not has_conflict,
        )

    def get_operation_availability(
        self,
        truck_id: uuid.UUID,
        driver_id: uuid.UUID,
    ) -> OperationAvailability:
        truck = self.get_truck_availability(truck_id)
        driver = self.get_driver_availability(driver_id)

        return OperationAvailability(
            truck=truck,
            driver=driver,
            available=truck.available and driver.available,
        )
