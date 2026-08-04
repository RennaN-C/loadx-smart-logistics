import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.trucks.models import Truck


class TruckRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> Sequence[Truck]:
        statement = select(Truck).order_by(Truck.created_at.desc(), Truck.plate.asc())
        return self.db.scalars(statement).all()

    def get(self, truck_id: uuid.UUID) -> Truck | None:
        return self.db.get(Truck, truck_id)

    def get_for_update(self, truck_id: uuid.UUID) -> Truck | None:
        statement = select(Truck).where(Truck.id == truck_id).with_for_update()
        return self.db.scalar(statement)

    def get_by_plate(self, plate: str) -> Truck | None:
        statement = select(Truck).where(Truck.plate == plate)
        return self.db.scalar(statement)

    def add(self, truck: Truck) -> Truck:
        self.db.add(truck)
        self.db.flush()
        self.db.refresh(truck)
        return truck

    def update(self, truck: Truck) -> Truck:
        self.db.add(truck)
        self.db.flush()
        self.db.refresh(truck)
        return truck
