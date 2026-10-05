from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.modules.deliveries.reference_service import (
    DeliveryReferenceService,
    DeliveryStatusCounts,
    TripStatusCounts,
)
from app.modules.occurrences.reference_service import OccurrenceReferenceService
from app.modules.operational_indicators.service import (
    DeliveryIndicators,
    FleetIndicators,
    OccurrenceIndicators,
    OperationalIndicators,
    OperationalIndicatorsService,
    TripIndicators,
)
from app.modules.trucks.operational_status_service import (
    TruckOperationalStatusService,
    TruckOperationalSummary,
)


def make_service(
    *,
    fleet: TruckOperationalSummary,
    trips: TripStatusCounts,
    deliveries: DeliveryStatusCounts,
    occurrences: int,
) -> tuple[
    OperationalIndicatorsService,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    truck_status_service = MagicMock(spec=TruckOperationalStatusService)
    truck_status_service.get_summary.return_value = fleet

    delivery_reference_service = MagicMock(spec=DeliveryReferenceService)
    delivery_reference_service.get_trip_status_counts.return_value = trips
    delivery_reference_service.get_delivery_status_counts.return_value = deliveries

    occurrence_reference_service = MagicMock(spec=OccurrenceReferenceService)
    occurrence_reference_service.count_occurrences.return_value = occurrences

    service = OperationalIndicatorsService(
        MagicMock(spec=Session),
        truck_status_service=truck_status_service,
        delivery_reference_service=delivery_reference_service,
        occurrence_reference_service=occurrence_reference_service,
    )

    return (
        service,
        truck_status_service,
        delivery_reference_service,
        occurrence_reference_service,
    )


def test_get_indicators_consolidates_supported_sources() -> None:
    service, truck_service, delivery_service, occurrence_service = make_service(
        fleet=TruckOperationalSummary(
            total=4,
            active=3,
            inactive=1,
            available=1,
            unavailable=3,
            with_operation_conflict=2,
        ),
        trips=TripStatusCounts(
            total=3,
            scheduled=1,
            in_route=1,
            finished=1,
        ),
        deliveries=DeliveryStatusCounts(
            total=6,
            pending=3,
            in_delivery=1,
            delivered=2,
        ),
        occurrences=2,
    )

    result = service.get_indicators()

    assert result == OperationalIndicators(
        fleet=FleetIndicators(
            period="CURRENT_SNAPSHOT",
            total=4,
            active=3,
            inactive=1,
            available=1,
            unavailable=3,
            with_operation_conflict=2,
        ),
        trips=TripIndicators(
            period="ALL_TIME",
            total=3,
            scheduled=1,
            in_route=1,
            finished=1,
        ),
        deliveries=DeliveryIndicators(
            period="ALL_TIME",
            total=6,
            pending=3,
            in_delivery=1,
            delivered=2,
        ),
        occurrences=OccurrenceIndicators(
            period="ALL_TIME",
            total=2,
        ),
    )

    truck_service.get_summary.assert_called_once_with()
    delivery_service.get_trip_status_counts.assert_called_once_with()
    delivery_service.get_delivery_status_counts.assert_called_once_with()
    occurrence_service.count_occurrences.assert_called_once_with()


def test_get_indicators_returns_zeroes_for_empty_sources() -> None:
    service, _, _, _ = make_service(
        fleet=TruckOperationalSummary(
            total=0,
            active=0,
            inactive=0,
            available=0,
            unavailable=0,
            with_operation_conflict=0,
        ),
        trips=TripStatusCounts(
            total=0,
            scheduled=0,
            in_route=0,
            finished=0,
        ),
        deliveries=DeliveryStatusCounts(
            total=0,
            pending=0,
            in_delivery=0,
            delivered=0,
        ),
        occurrences=0,
    )

    result = service.get_indicators()

    assert result.fleet.total == 0
    assert result.trips.total == 0
    assert result.deliveries.total == 0
    assert result.occurrences.total == 0


def test_get_indicators_is_deterministic_for_same_sources() -> None:
    service, _, _, _ = make_service(
        fleet=TruckOperationalSummary(
            total=1,
            active=1,
            inactive=0,
            available=1,
            unavailable=0,
            with_operation_conflict=0,
        ),
        trips=TripStatusCounts(
            total=1,
            scheduled=1,
            in_route=0,
            finished=0,
        ),
        deliveries=DeliveryStatusCounts(
            total=2,
            pending=2,
            in_delivery=0,
            delivered=0,
        ),
        occurrences=0,
    )

    first_result = service.get_indicators()
    second_result = service.get_indicators()

    assert first_result == second_result
