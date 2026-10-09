import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.drivers.document_history import stage_license_history
from app.modules.drivers.document_repository import DocumentRepository
from app.modules.drivers.models import Driver
from app.modules.drivers.repository import DriverRepository
from app.modules.drivers.schemas import DriverCreate, DriverUpdate
from app.shared.record_lifecycle import stage_lifecycle_event, validate_reactivation


class DriverNotFoundError(Exception):
    pass


class DriverDocumentAlreadyExistsError(Exception):
    pass


class DriverLicenseNumberAlreadyExistsError(Exception):
    pass


class DriverOperationConflictError(Exception):
    def __init__(self, driver_id: uuid.UUID) -> None:
        self.driver_id = driver_id
        super().__init__("driver is reserved by another active trip")


class DriverService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DriverRepository(db)

    def list_drivers(
        self, pagination: PaginationParams, *, active: bool | None = None
    ) -> PageResult[Driver]:
        return self.repository.list(pagination, active=active)

    def get_driver(self, driver_id: uuid.UUID) -> Driver:
        driver = self.repository.get(driver_id)
        if driver is None:
            raise DriverNotFoundError
        return driver

    def get_driver_for_update(self, driver_id: uuid.UUID) -> Driver:
        driver = self.repository.get_for_update(driver_id)
        if driver is None:
            raise DriverNotFoundError
        return driver

    def has_operation_conflict(
        self,
        driver_id: uuid.UUID,
        *,
        exclude_trip_id: uuid.UUID | None = None,
    ) -> bool:
        return bool(
            DeliveryReferenceService(self.db).list_active_trips_for_driver(
                driver_id,
                exclude_trip_id=exclude_trip_id,
            )
        )

    def ensure_no_operation_conflict(
        self,
        driver_id: uuid.UUID,
        *,
        exclude_trip_id: uuid.UUID | None = None,
    ) -> Driver:
        driver = self.get_driver_for_update(driver_id)
        self.ensure_operational_eligibility(driver_id)
        if self.has_operation_conflict(driver_id, exclude_trip_id=exclude_trip_id):
            raise DriverOperationConflictError(driver_id)
        return driver

    def has_document_conflict(
        self, driver_id: uuid.UUID, *, at: datetime | None = None
    ) -> bool:
        return DocumentRepository(self.db).has_block(driver_id, at or datetime.now(UTC))

    def ensure_operational_eligibility(self, driver_id: uuid.UUID) -> None:
        if self.has_document_conflict(driver_id):
            raise ApiError(
                409,
                "DRIVER_DOCUMENT_INELIGIBLE",
                "Motorista indisponível pela política documental.",
            )

    def create_driver(
        self, data: DriverCreate, *, changed_by: uuid.UUID | None = None
    ) -> Driver:
        return self._persist(
            lambda: self.stage_create_driver(data, changed_by=changed_by)
        )

    def stage_create_driver(
        self, data: DriverCreate, *, changed_by: uuid.UUID | None = None
    ) -> Driver:
        """Stage native CNH/history and creation without committing the caller."""
        if self.repository.get_by_document(data.document) is not None:
            raise DriverDocumentAlreadyExistsError
        if self.repository.get_by_license_number(data.license_number) is not None:
            raise DriverLicenseNumberAlreadyExistsError
        driver = self.repository.add(Driver(**data.model_dump()))
        stage_license_history(self.db, driver, actor=changed_by)
        return driver

    def existing_registration_keys(
        self, keys: dict[str, set[str]]
    ) -> dict[str, set[str]]:
        """Public batched uniqueness boundary, including archived registrations."""
        return self.repository.existing_registration_keys(keys)

    def update_driver(
        self,
        driver_id: uuid.UUID,
        data: DriverUpdate,
        *,
        changed_by: uuid.UUID | None = None,
    ) -> Driver:
        driver = self.repository.get_for_update(driver_id)
        if driver is None:
            raise DriverNotFoundError
        old_active = driver.active
        update_data = data.model_dump(exclude_unset=True)

        new_document = update_data.get("document")
        if new_document is not None and new_document != driver.document:
            existing_driver = self.repository.get_by_document(new_document)
            if existing_driver is not None and existing_driver.id != driver.id:
                raise DriverDocumentAlreadyExistsError

        new_license_number = update_data.get("license_number")
        if (
            new_license_number is not None
            and new_license_number != driver.license_number
        ):
            existing_driver = self.repository.get_by_license_number(new_license_number)
            if existing_driver is not None and existing_driver.id != driver.id:
                raise DriverLicenseNumberAlreadyExistsError

        for field_name, value in update_data.items():
            setattr(driver, field_name, value)

        def stage_update() -> Driver:
            if not old_active and driver.active:
                validate_reactivation(DriverCreate, driver)
            self.repository.update(driver)
            stage_license_history(self.db, driver, actor=changed_by)
            stage_lifecycle_event(
                self.db,
                entity_type="DRIVER",
                entity_id=driver.id,
                old_active=old_active,
                new_active=driver.active,
                changed_by=changed_by,
            )
            return driver

        return self._persist(stage_update)

    def _persist(self, operation: Callable[[], Driver]) -> Driver:
        try:
            driver = operation()
            self.db.commit()
            self.db.refresh(driver)
        except IntegrityError as exc:
            self.db.rollback()
            constraint_name = get_integrity_constraint_name(exc)
            if constraint_name == "uq_drivers__license_number":
                raise DriverLicenseNumberAlreadyExistsError from exc
            if constraint_name == "uq_drivers__document":
                raise DriverDocumentAlreadyExistsError from exc
            raise
        except Exception:
            self.db.rollback()
            raise
        return driver
