import uuid

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.drivers.models import Driver


class DriverRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self, pagination: PaginationParams, *, active: bool | None = None
    ) -> PageResult[Driver]:
        direction = asc if pagination.sort_order == "asc" else desc
        filters = () if active is None else (Driver.active.is_(active),)
        total = (
            self.db.scalar(select(func.count()).select_from(Driver).where(*filters))
            or 0
        )
        statement = (
            select(Driver)
            .where(*filters)
            .order_by(direction(Driver.created_at), direction(Driver.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return PageResult.create(
            self.db.scalars(statement).all(),
            pagination,
            total,
        )

    def get(self, driver_id: uuid.UUID) -> Driver | None:
        return self.db.get(Driver, driver_id)

    def get_for_update(self, driver_id: uuid.UUID) -> Driver | None:
        statement = (
            select(Driver)
            .where(Driver.id == driver_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(statement)

    def existing_registration_keys(
        self, keys: dict[str, set[str]]
    ) -> dict[str, set[str]]:
        return {
            field: set(
                self.db.scalars(
                    select(getattr(Driver, field)).where(
                        getattr(Driver, field).in_(keys.get(field, set()))
                    )
                )
            )
            for field in ("document", "license_number")
        }

    def get_by_document(self, document: str) -> Driver | None:
        statement = select(Driver).where(Driver.document == document)
        return self.db.scalar(statement)

    def get_by_license_number(self, license_number: str) -> Driver | None:
        statement = select(Driver).where(Driver.license_number == license_number)
        return self.db.scalar(statement)

    def get_by_phone(self, phone: str) -> Driver | None:
        statement = (
            select(Driver).where(Driver.phone == phone).order_by(Driver.id).limit(2)
        )
        drivers = tuple(self.db.scalars(statement))
        return drivers[0] if len(drivers) == 1 else None

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
