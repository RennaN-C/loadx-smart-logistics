import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.modules.deliveries.models import Trip
from app.modules.drivers.models import Driver
from app.modules.load_planning.models import LoadPlan
from app.modules.loading.models import LoadingSession
from app.modules.trucks.models import Truck
from app.modules.trucks.service import (
    TruckOperationConflictError,
    TruckService,
)

SQLITE_TABLES = (
    Truck.__table__,
    Driver.__table__,
    LoadPlan.__table__,
    LoadingSession.__table__,
    Trip.__table__,
)


def create_truck(db: Session) -> Truck:
    truck = Truck(
        plate=f"T{uuid.uuid4().hex[:6]}",
        model="Caminhao conflito",
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=Decimal("1000.00"),
        active=True,
    )
    db.add(truck)
    db.flush()
    return truck


def create_driver(db: Session) -> Driver:
    driver = Driver(
        name="Motorista conflito",
        document=f"DOC-{uuid.uuid4()}",
        phone="41999999999",
        license_number=f"CNH-{uuid.uuid4()}",
        license_category="D",
        active=True,
    )
    db.add(driver)
    db.flush()
    return driver


def create_plan(db: Session, truck: Truck) -> LoadPlan:
    plan = LoadPlan(
        truck_id=truck.id,
        status="APPROVED",
        truck_snapshot_plate=truck.plate,
        truck_snapshot_model=truck.model,
        truck_snapshot_internal_width_cm=100,
        truck_snapshot_internal_height_cm=100,
        truck_snapshot_internal_length_cm=100,
        truck_snapshot_max_weight_kg=Decimal("1000.00"),
        internal_volume_cm3=1_000_000,
        used_volume_cm3=1_000,
        occupancy_percent=Decimal("0.10"),
        total_weight_kg=Decimal("1.000"),
        loaded_count=1,
        unloaded_count=0,
        algorithm_version="conflict-test-v1",
        approved_at=datetime.now(UTC),
    )
    db.add(plan)
    db.flush()
    return plan


def test_approved_plan_without_operation_keeps_truck_available(
    db_session: Session,
) -> None:
    truck = create_truck(db_session)
    create_plan(db_session, truck)
    db_session.commit()

    service = TruckService(db_session)

    assert not service.has_operation_conflict(truck.id)


def test_loading_session_reserves_truck(
    db_session: Session,
) -> None:
    truck = create_truck(db_session)
    plan = create_plan(db_session, truck)
    db_session.add(
        LoadingSession(
            load_plan_id=plan.id,
            status="PENDING",
        )
    )
    db_session.commit()

    service = TruckService(db_session)

    assert service.has_operation_conflict(truck.id)
    assert not service.has_operation_conflict(
        truck.id,
        exclude_load_plan_id=plan.id,
    )


def test_finished_loading_without_trip_keeps_truck_reserved(
    db_session: Session,
) -> None:
    truck = create_truck(db_session)
    plan = create_plan(db_session, truck)
    now = datetime.now(UTC)

    db_session.add(
        LoadingSession(
            load_plan_id=plan.id,
            status="FINISHED",
            started_at=now,
            finished_at=now,
        )
    )
    db_session.commit()

    service = TruckService(db_session)

    assert service.has_operation_conflict(truck.id)


@pytest.mark.parametrize("status", ["SCHEDULED", "IN_ROUTE"])
def test_active_trip_reserves_truck(
    db_session: Session,
    status: str,
) -> None:
    truck = create_truck(db_session)
    driver = create_driver(db_session)
    plan = create_plan(db_session, truck)

    db_session.add(
        Trip(
            load_plan_id=plan.id,
            driver_id=driver.id,
            status=status,
            started_at=datetime.now(UTC) if status == "IN_ROUTE" else None,
        )
    )
    db_session.commit()

    service = TruckService(db_session)

    assert service.has_operation_conflict(truck.id)


def test_finished_trip_releases_truck(
    db_session: Session,
) -> None:
    truck = create_truck(db_session)
    driver = create_driver(db_session)
    plan = create_plan(db_session, truck)
    now = datetime.now(UTC)

    db_session.add(
        LoadingSession(
            load_plan_id=plan.id,
            status="FINISHED",
            started_at=now,
            finished_at=now,
        )
    )
    db_session.add(
        Trip(
            load_plan_id=plan.id,
            driver_id=driver.id,
            status="FINISHED",
            started_at=now,
            finished_at=now,
        )
    )
    db_session.commit()

    service = TruckService(db_session)

    assert not service.has_operation_conflict(truck.id)


def test_other_plan_using_same_truck_causes_conflict(
    db_session: Session,
) -> None:
    truck = create_truck(db_session)
    current_plan = create_plan(db_session, truck)
    other_plan = create_plan(db_session, truck)

    db_session.add(
        LoadingSession(
            load_plan_id=other_plan.id,
            status="PENDING",
        )
    )
    db_session.commit()

    service = TruckService(db_session)

    with pytest.raises(TruckOperationConflictError) as exc_info:
        service.ensure_no_operation_conflict(
            truck.id,
            exclude_load_plan_id=current_plan.id,
        )

    assert exc_info.value.truck_id == truck.id

    assert (
        service.ensure_no_operation_conflict(
            truck.id,
            exclude_load_plan_id=other_plan.id,
        ).id
        == truck.id
    )
