import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.drivers.operational_status_service import (
    DriverOperationalStatusService,
)
from app.modules.drivers.service import DriverService
from app.modules.fleet.service import DriverAvailability, FleetAvailabilityService


@pytest.mark.parametrize(
    ("active", "conflict", "available"),
    [
        (True, False, True),
        (True, True, False),
        (False, False, False),
    ],
)
def test_list_statuses_uses_oc67_result_without_recalculating_rules(
    active: bool,
    conflict: bool,
    available: bool,
) -> None:
    driver_id = uuid.uuid4()
    driver = SimpleNamespace(
        id=driver_id,
        name="Carlos Pereira",
        license_category="D",
    )
    pagination = PaginationParams(page=2, page_size=5, sort_order="asc")

    driver_service = MagicMock(spec=DriverService)
    driver_service.list_drivers.return_value = PageResult(
        items=(driver,),
        page=2,
        page_size=5,
        total=7,
        total_pages=2,
    )

    fleet_service = MagicMock(spec=FleetAvailabilityService)
    fleet_service.get_driver_availability.return_value = DriverAvailability(
        driver_id=driver_id,
        active=active,
        has_operation_conflict=conflict,
        available=available,
    )

    service = DriverOperationalStatusService(
        MagicMock(spec=Session),
        driver_service=driver_service,
        fleet_service=fleet_service,
    )

    result = service.list_statuses(pagination)

    assert result.page == 2
    assert result.page_size == 5
    assert result.total == 7
    assert result.total_pages == 2
    assert len(result.items) == 1

    item = result.items[0]
    assert item.id == driver_id
    assert item.name == "Carlos Pereira"
    assert item.license_category == "D"
    assert item.active is active
    assert item.has_operation_conflict is conflict
    assert item.available is available

    driver_service.list_drivers.assert_called_once_with(pagination)
    fleet_service.get_driver_availability.assert_called_once_with(driver_id)


def test_list_statuses_preserves_empty_page_without_availability_queries() -> None:
    pagination = PaginationParams(page=1, page_size=20, sort_order="desc")

    driver_service = MagicMock(spec=DriverService)
    driver_service.list_drivers.return_value = PageResult(
        items=(),
        page=1,
        page_size=20,
        total=0,
        total_pages=0,
    )
    fleet_service = MagicMock(spec=FleetAvailabilityService)

    service = DriverOperationalStatusService(
        MagicMock(spec=Session),
        driver_service=driver_service,
        fleet_service=fleet_service,
    )

    result = service.list_statuses(pagination)

    assert result.items == ()
    assert result.total == 0
    assert result.total_pages == 0
    fleet_service.get_driver_availability.assert_not_called()
