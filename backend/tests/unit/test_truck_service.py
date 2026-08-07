import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.modules.trucks.models import Truck
from app.modules.trucks.schemas import TruckCreate, TruckUpdate
from app.modules.trucks.service import (
    TruckNotFoundError,
    TruckPlateAlreadyExistsError,
    TruckService,
)

SQLITE_TABLES = (Truck.__table__,)


def make_truck_create(plate: str = "ABC1D23") -> TruckCreate:
    return TruckCreate(
        plate=plate,
        model="Bau medio",
        internal_width_cm=240,
        internal_height_cm=260,
        internal_length_cm=600,
        max_weight_kg=Decimal("8000.00"),
    )


def test_create_truck_persists_normalized_plate(db_session: Session) -> None:
    service = TruckService(db_session)

    truck = service.create_truck(make_truck_create("abc1d23"))

    assert truck.id is not None
    assert truck.plate == "ABC1D23"
    assert truck.active is True


def test_create_truck_rejects_duplicate_plate(db_session: Session) -> None:
    service = TruckService(db_session)
    service.create_truck(make_truck_create("ABC1D23"))

    with pytest.raises(TruckPlateAlreadyExistsError):
        service.create_truck(make_truck_create("abc1d23"))


def test_update_truck_rejects_duplicate_plate(db_session: Session) -> None:
    service = TruckService(db_session)
    first_truck = service.create_truck(make_truck_create("ABC1D23"))
    service.create_truck(make_truck_create("XYZ9A88"))

    with pytest.raises(TruckPlateAlreadyExistsError):
        service.update_truck(first_truck.id, TruckUpdate(plate="XYZ9A88"))


def test_get_truck_raises_when_not_found(db_session: Session) -> None:
    service = TruckService(db_session)

    with pytest.raises(TruckNotFoundError):
        service.get_truck(uuid.uuid4())
