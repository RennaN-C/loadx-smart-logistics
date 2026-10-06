import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.deliveries.schemas import TripCreate
from app.modules.deliveries.service import TripService
from app.modules.drivers.service import (
    DriverNotFoundError,
    DriverOperationConflictError,
    DriverService,
)
from app.modules.loading.models import LoadingSession
from app.modules.status_history.models import StatusHistory
from tests.unit.test_delivery_service import (
    SQLITE_TABLES,  # noqa: F401
    create_trip,
    seed_operational_plan,
)


def test_plan_and_loading_without_trip_do_not_reserve_driver(
    db_session: Session,
) -> None:
    _, driver, plan, _ = seed_operational_plan(db_session)
    db_session.add(LoadingSession(load_plan_id=plan.id, status="PENDING"))
    db_session.commit()
    service = DriverService(db_session)
    assert not service.has_operation_conflict(driver.id)
    assert service.ensure_no_operation_conflict(driver.id).id == driver.id


@pytest.mark.parametrize("status", ["SCHEDULED", "IN_ROUTE"])
def test_active_trip_rejects_other_plan_and_rolls_back(
    db_session: Session, status: str
) -> None:
    service, manager, driver, trip, _ = create_trip(db_session, loading_finished=True)
    if status == "IN_ROUTE":
        service.change_trip_status(trip.id, status, current_user=manager)
    _, other_driver, other_plan, orders = seed_operational_plan(db_session)
    driver_service = DriverService(db_session)
    history_count = len(db_session.scalars(select(StatusHistory)).all())
    assert driver_service.has_operation_conflict(driver.id)
    assert not driver_service.has_operation_conflict(other_driver.id)
    assert not driver_service.has_operation_conflict(driver.id, exclude_trip_id=trip.id)
    with pytest.raises(DriverOperationConflictError) as exc:
        service.create_trip(
            TripCreate(load_plan_id=other_plan.id, driver_id=driver.id),
            changed_by=manager.id,
        )
    assert exc.value.driver_id == driver.id
    assert len(db_session.scalars(select(Trip)).all()) == 1
    assert len(db_session.scalars(select(Delivery)).all()) == 2
    assert len(db_session.scalars(select(StatusHistory)).all()) == history_count
    assert all(order.status == "PLANNED" for order in orders)


def test_only_finished_trip_releases_driver_for_new_allocation(
    db_session: Session,
) -> None:
    service, manager, driver, trip, _ = create_trip(db_session, loading_finished=True)
    driver_service = DriverService(db_session)
    service.change_trip_status(trip.id, "IN_ROUTE", current_user=manager)
    for delivery in trip.deliveries:
        for status in ("IN_DELIVERY", "DELIVERED"):
            service.change_delivery_status(delivery.id, status, current_user=manager)
    assert driver_service.has_operation_conflict(driver.id)
    service.change_trip_status(trip.id, "FINISHED", current_user=manager)
    assert not driver_service.has_operation_conflict(driver.id)
    _, _, plan, _ = seed_operational_plan(db_session)
    next_trip = service.create_trip(
        TripCreate(load_plan_id=plan.id, driver_id=driver.id), changed_by=manager.id
    )
    assert next_trip.driver_id == trip.driver_id
    assert driver_service.has_operation_conflict(driver.id)


def test_legacy_conflict_blocks_start_but_preserves_idempotency(
    db_session: Session,
) -> None:
    service, manager, driver, trip, _ = create_trip(db_session, loading_finished=True)
    _, _, plan, _ = seed_operational_plan(db_session)
    other_trip = Trip(load_plan_id=plan.id, driver_id=driver.id, status="SCHEDULED")
    db_session.add(other_trip)
    db_session.commit()
    reference = DeliveryReferenceService(db_session)
    assert reference.get_active_trip_for_driver(driver.id) is None
    assert DriverService(db_session).has_operation_conflict(driver.id)
    assert DriverService(db_session).has_operation_conflict(
        driver.id, exclude_trip_id=trip.id
    )
    with pytest.raises(DriverOperationConflictError):
        service.change_trip_status(trip.id, "IN_ROUTE", current_user=manager)
    assert trip.status == "SCHEDULED"
    assert trip.started_at is None
    assert (
        service.change_trip_status(trip.id, "SCHEDULED", current_user=manager).id
        == trip.id
    )


def test_missing_driver_validation_is_separate_from_conflict(
    db_session: Session,
) -> None:
    service = DriverService(db_session)
    driver_id = uuid.uuid4()
    assert not service.has_operation_conflict(driver_id)
    with pytest.raises(DriverNotFoundError):
        service.ensure_no_operation_conflict(driver_id)


def test_failed_creation_does_not_reserve_driver(
    db_session: Session, monkeypatch
) -> None:
    manager, driver, plan, _ = seed_operational_plan(db_session)
    service = TripService(db_session)

    def fail_history(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(service, "_stage_status_change", fail_history)
    with pytest.raises(RuntimeError):
        service.create_trip(
            TripCreate(load_plan_id=plan.id, driver_id=driver.id), changed_by=manager.id
        )
    assert not DriverService(db_session).has_operation_conflict(driver.id)
    assert not db_session.scalars(select(Trip)).all()
    assert not db_session.scalars(select(Delivery)).all()
