import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.drivers.models import Driver


class DriverRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> Sequence[Driver]:
        statement = select(Driver).order_by(Driver.created_at.desc(), Driver.name.asc())
        return self.db.scalars(statement).all()

    def get(self, driver_id: uuid.UUID) -> Driver | None:
        return self.db.get(Driver, driver_id)

    def get_by_document(self, document: str) -> Driver | None:
        statement = select(Driver).where(Driver.document == document)
        return self.db.scalar(statement)

    def get_by_license_number(self, license_number: str) -> Driver | None:
        statement = select(Driver).where(Driver.license_number == license_number)
        return self.db.scalar(statement)

    def add(self, driver: Driver) -> Driver:
        self.db.add(driver)
        self.db.flush()
        self.db.refresh(driver)
        return driver

    def update(self, driver: Driver) -> Driver:
        self.db.add(driver)
        self.db.flush()
        self.db.refresh(driver)
        return driver
