import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.modules.drivers.service import DriverNotFoundError, DriverService
from app.modules.fleet.service import FleetAvailabilityService
from app.modules.trucks.service import TruckNotFoundError, TruckService


def make_service(
    *,
    truck_active: bool = True,
    truck_conflict: bool = False,
    driver_active: bool = True,
    driver_conflict: bool = False,
) -> tuple[FleetAvailabilityService, MagicMock, MagicMock]:
    truck_id = uuid.uuid4()
    driver_id = uuid.uuid4()

    truck_service = MagicMock(spec=TruckService)
    truck_service.get_truck.return_value = SimpleNamespace(
        id=truck_id,
        active=truck_active,
    )
    truck_service.has_operation_conflict.return_value = truck_conflict

    driver_service = MagicMock(spec=DriverService)
    driver_service.get_driver.return_value = SimpleNamespace(
        id=driver_id,
        active=driver_active,
    )
    driver_service.has_operation_conflict.return_value = driver_conflict

    db = MagicMock(spec=Session)

    service = FleetAvailabilityService(
        db,
        truck_service=truck_service,
        driver_service=driver_service,
    )

    return service, truck_service, driver_service


@pytest.mark.parametrize(
    ("active", "conflict", "expected"),
    [
        (True, False, True),
        (True, True, False),
        (False, False, False),
        (False, True, False),
    ],
)
def test_get_truck_availability_combines_active_and_conflict(
    active: bool,
    conflict: bool,
    expected: bool,
) -> None:
    service, truck_service, _ = make_service(
        truck_active=active,
        truck_conflict=conflict,
    )

    truck = truck_service.get_truck.return_value

    result = service.get_truck_availability(truck.id)

    assert result.truck_id == truck.id
    assert result.active is active
    assert result.has_operation_conflict is conflict
    assert result.available is expected

    truck_service.get_truck.assert_called_once_with(truck.id)
    truck_service.has_operation_conflict.assert_called_once_with(truck.id)


@pytest.mark.parametrize(
    ("active", "conflict", "expected"),
    [
        (True, False, True),
        (True, True, False),
        (False, False, False),
        (False, True, False),
    ],
)
def test_get_driver_availability_combines_active_and_conflict(
    active: bool,
    conflict: bool,
    expected: bool,
) -> None:
    service, _, driver_service = make_service(
        driver_active=active,
        driver_conflict=conflict,
    )

    driver = driver_service.get_driver.return_value

    result = service.get_driver_availability(driver.id)

    assert result.driver_id == driver.id
    assert result.active is active
    assert result.has_operation_conflict is conflict
    assert result.available is expected

    driver_service.get_driver.assert_called_once_with(driver.id)
    driver_service.has_operation_conflict.assert_called_once_with(driver.id)


@pytest.mark.parametrize(
    (
        "truck_active",
        "truck_conflict",
        "driver_active",
        "driver_conflict",
        "expected",
    ),
    [
        (True, False, True, False, True),
        (True, True, True, False, False),
        (True, False, True, True, False),
        (False, False, True, False, False),
        (True, False, False, False, False),
    ],
)
def test_get_operation_availability_requires_both_resources_available(
    truck_active: bool,
    truck_conflict: bool,
    driver_active: bool,
    driver_conflict: bool,
    expected: bool,
) -> None:
    service, truck_service, driver_service = make_service(
        truck_active=truck_active,
        truck_conflict=truck_conflict,
        driver_active=driver_active,
        driver_conflict=driver_conflict,
    )

    truck = truck_service.get_truck.return_value
    driver = driver_service.get_driver.return_value

    result = service.get_operation_availability(
        truck.id,
        driver.id,
    )

    assert result.truck.truck_id == truck.id
    assert result.driver.driver_id == driver.id
    assert result.available is expected


def test_truck_not_found_error_is_preserved() -> None:
    service, truck_service, _ = make_service()
    truck_id = uuid.uuid4()
    truck_service.get_truck.side_effect = TruckNotFoundError

    with pytest.raises(TruckNotFoundError):
        service.get_truck_availability(truck_id)

    truck_service.has_operation_conflict.assert_not_called()


def test_driver_not_found_error_is_preserved() -> None:
    service, _, driver_service = make_service()
    driver_id = uuid.uuid4()
    driver_service.get_driver.side_effect = DriverNotFoundError

    with pytest.raises(DriverNotFoundError):
        service.get_driver_availability(driver_id)

    driver_service.has_operation_conflict.assert_not_called()
