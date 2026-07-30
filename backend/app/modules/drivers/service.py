import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.drivers.models import Driver
from app.modules.drivers.repository import DriverRepository
from app.modules.drivers.schemas import DriverCreate, DriverUpdate


class DriverNotFoundError(Exception):
    pass


class DriverDocumentAlreadyExistsError(Exception):
    pass


class DriverLicenseNumberAlreadyExistsError(Exception):
    pass


class DriverService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DriverRepository(db)

    def list_drivers(self) -> Sequence[Driver]:
        return self.repository.list()

    def get_driver(self, driver_id: uuid.UUID) -> Driver:
        driver = self.repository.get(driver_id)
        if driver is None:
            raise DriverNotFoundError
        return driver

    def create_driver(self, data: DriverCreate) -> Driver:
        if self.repository.get_by_document(data.document) is not None:
            raise DriverDocumentAlreadyExistsError
        if self.repository.get_by_license_number(data.license_number) is not None:
            raise DriverLicenseNumberAlreadyExistsError

        driver = Driver(**data.model_dump())
        return self._persist(lambda: self.repository.add(driver))

    def update_driver(self, driver_id: uuid.UUID, data: DriverUpdate) -> Driver:
        driver = self.get_driver(driver_id)
        update_data = data.model_dump(exclude_unset=True)

        new_document = update_data.get("document")
        if new_document is not None and new_document != driver.document:
            existing_driver = self.repository.get_by_document(new_document)
            if existing_driver is not None and existing_driver.id != driver.id:
                raise DriverDocumentAlreadyExistsError

        new_license_number = update_data.get("license_number")
        if new_license_number is not None and new_license_number != driver.license_number:
            existing_driver = self.repository.get_by_license_number(new_license_number)
            if existing_driver is not None and existing_driver.id != driver.id:
                raise DriverLicenseNumberAlreadyExistsError

        for field_name, value in update_data.items():
            setattr(driver, field_name, value)

        return self._persist(lambda: self.repository.update(driver))

    def _persist(self, operation: Callable[[], Driver]) -> Driver:
        try:
            driver = operation()
            self.db.commit()
            self.db.refresh(driver)
        except IntegrityError as exc:
            self.db.rollback()
            if "license_number" in str(exc.orig).lower():
                raise DriverLicenseNumberAlreadyExistsError from exc
            raise DriverDocumentAlreadyExistsError from exc
        return driver
