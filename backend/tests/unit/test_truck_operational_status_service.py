import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.core.pagination import PageResult, PaginationParams
from app.modules.fleet.service import FleetAvailabilityService, TruckAvailability
from app.modules.trucks.operational_status_service import TruckOperationalStatusService
from app.modules.trucks.service import TruckService
from sqlalchemy.orm import Session


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
    truck_id = uuid.uuid4()
    truck = SimpleNamespace(
        id=truck_id,
        plate="ABC1D23",
        model="Bau medio",
    )
    pagination = PaginationParams(page=2, page_size=5, sort_order="asc")

    truck_service = MagicMock(spec=TruckService)
    truck_service.list_trucks.return_value = PageResult(
        items=(truck,),
        page=2,
        page_size=5,
        total=7,
        total_pages=2,
    )

    fleet_service = MagicMock(spec=FleetAvailabilityService)
    fleet_service.get_truck_availability.return_value = TruckAvailability(
        truck_id=truck_id,
        active=active,
        has_operation_conflict=conflict,
        available=available,
    )

    service = TruckOperationalStatusService(
        MagicMock(spec=Session),
        truck_service=truck_service,
        fleet_service=fleet_service,
    )

    result = service.list_statuses(pagination)

    assert result.page == 2
    assert result.page_size == 5
    assert result.total == 7
    assert result.total_pages == 2
    assert len(result.items) == 1

    item = result.items[0]
    assert item.id == truck_id
    assert item.plate == "ABC1D23"
    assert item.model == "Bau medio"
    assert item.active is active
    assert item.has_operation_conflict is conflict
    assert item.available is available

    truck_service.list_trucks.assert_called_once_with(pagination)
    fleet_service.get_truck_availability.assert_called_once_with(truck_id)


def test_list_statuses_preserves_empty_page_without_availability_queries() -> None:
    pagination = PaginationParams(page=1, page_size=20, sort_order="desc")

    truck_service = MagicMock(spec=TruckService)
    truck_service.list_trucks.return_value = PageResult(
        items=(),
        page=1,
        page_size=20,
        total=0,
        total_pages=0,
    )

    fleet_service = MagicMock(spec=FleetAvailabilityService)

    service = TruckOperationalStatusService(
        MagicMock(spec=Session),
        truck_service=truck_service,
        fleet_service=fleet_service,
    )

    result = service.list_statuses(pagination)

    assert result.items == ()
    assert result.total == 0
    assert result.total_pages == 0
    fleet_service.get_truck_availability.assert_not_called()
