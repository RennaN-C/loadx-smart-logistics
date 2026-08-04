import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import get_integrity_constraint_name
from app.modules.trucks.models import Truck
from app.modules.trucks.repository import TruckRepository
from app.modules.trucks.schemas import TruckCreate, TruckUpdate


class TruckNotFoundError(Exception):
    pass


class TruckPlateAlreadyExistsError(Exception):
    pass


class TruckService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TruckRepository(db)

    def list_trucks(self) -> Sequence[Truck]:
        return self.repository.list()

    def get_truck(self, truck_id: uuid.UUID) -> Truck:
        truck = self.repository.get(truck_id)
        if truck is None:
            raise TruckNotFoundError
        return truck

    def get_truck_for_update(self, truck_id: uuid.UUID) -> Truck:
        truck = self.repository.get_for_update(truck_id)
        if truck is None:
            raise TruckNotFoundError
        return truck

    def create_truck(self, data: TruckCreate) -> Truck:
        if self.repository.get_by_plate(data.plate) is not None:
            raise TruckPlateAlreadyExistsError

        truck = Truck(**data.model_dump())
        return self._persist(lambda: self.repository.add(truck))

    def update_truck(self, truck_id: uuid.UUID, data: TruckUpdate) -> Truck:
        truck = self.get_truck(truck_id)
        update_data = data.model_dump(exclude_unset=True)

        new_plate = update_data.get("plate")
        if new_plate is not None and new_plate != truck.plate:
            existing_truck = self.repository.get_by_plate(new_plate)
            if existing_truck is not None and existing_truck.id != truck.id:
                raise TruckPlateAlreadyExistsError

        for field_name, value in update_data.items():
            setattr(truck, field_name, value)

        return self._persist(lambda: self.repository.update(truck))

    def _persist(self, operation: Callable[[], Truck]) -> Truck:
        try:
            truck = operation()
            self.db.commit()
            self.db.refresh(truck)
        except IntegrityError as exc:
            self.db.rollback()
            if get_integrity_constraint_name(exc) == "uq_trucks__plate":
                raise TruckPlateAlreadyExistsError from exc
            raise
        return truck
