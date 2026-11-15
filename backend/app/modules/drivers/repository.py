import uuid
from collections.abc import Sequence

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.drivers.models import Driver
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID
from app.shared.search import search_pattern


class DriverRepository:
    def __init__(
        self, db: Session, organization_id: uuid.UUID = LEGACY_ORGANIZATION_ID
    ) -> None:
        self.db = db
        self.organization_id = organization_id

    def list(
        self,
        pagination: PaginationParams,
        *,
        active: bool | None = None,
        search: str | None = None,
    ) -> PageResult[Driver]:
        direction = asc if pagination.sort_order == "asc" else desc
        filters = [Driver.organization_id == self.organization_id]
        if active is not None:
            filters.append(Driver.active.is_(active))
        pattern = search_pattern(search)
        if pattern is not None:
            filters.append(or_(Driver.name.ilike(pattern, escape="\\")))
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

    def names_for_ids(self, driver_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not driver_ids:
            return {}
        return dict(
            self.db.execute(
                select(Driver.id, Driver.name).where(
                    Driver.id.in_(driver_ids),
                    Driver.organization_id == self.organization_id,
                )
            ).all()
        )

    def get(self, driver_id: uuid.UUID) -> Driver | None:
        return self.db.scalar(
            select(Driver).where(
                Driver.id == driver_id,
                Driver.organization_id == self.organization_id,
            )
        )

    def get_for_update(self, driver_id: uuid.UUID) -> Driver | None:
        statement = (
            select(Driver)
            .where(
                Driver.id == driver_id,
                Driver.organization_id == self.organization_id,
            )
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
                        getattr(Driver, field).in_(keys.get(field, set())),
                        Driver.organization_id == self.organization_id,
                    )
                )
            )
            for field in ("document", "license_number")
        }

    def get_by_document(self, document: str) -> Driver | None:
        statement = select(Driver).where(
            Driver.document == document,
            Driver.organization_id == self.organization_id,
        )
        return self.db.scalar(statement)

    def get_by_license_number(self, license_number: str) -> Driver | None:
        statement = select(Driver).where(
            Driver.license_number == license_number,
            Driver.organization_id == self.organization_id,
        )
        return self.db.scalar(statement)

    def get_by_phone(self, phone: str) -> Driver | None:
        statement = (
            select(Driver)
            .where(
                Driver.phone == phone,
                Driver.organization_id == self.organization_id,
            )
            .order_by(Driver.id)
            .limit(2)
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
