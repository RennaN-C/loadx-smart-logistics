import uuid

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.customers.models import Customer
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID
from app.shared.search import search_pattern


class CustomerRepository:
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
    ) -> PageResult[Customer]:
        direction = asc if pagination.sort_order == "asc" else desc
        filters = [Customer.organization_id == self.organization_id]
        if active is not None:
            filters.append(Customer.active.is_(active))
        pattern = search_pattern(search)
        if pattern is not None:
            filters.append(
                or_(
                    Customer.name.ilike(pattern, escape="\\"),
                    Customer.city.ilike(pattern, escape="\\"),
                )
            )
        total = (
            self.db.scalar(select(func.count()).select_from(Customer).where(*filters))
            or 0
        )
        statement = (
            select(Customer)
            .where(*filters)
            .order_by(direction(Customer.created_at), direction(Customer.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return PageResult.create(
            self.db.scalars(statement).all(),
            pagination,
            total,
        )

    def matching_name_ids(self, search: str) -> Select[tuple[uuid.UUID]]:
        """Composable SQL projection; never materialize the customer collection."""
        return select(Customer.id).where(
            Customer.organization_id == self.organization_id,
            Customer.name.ilike(search_pattern(search), escape="\\")
        )

    def get(self, customer_id: uuid.UUID) -> Customer | None:
        return self.db.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.organization_id == self.organization_id,
            )
        )

    def get_for_update(self, customer_id: uuid.UUID) -> Customer | None:
        statement = (
            select(Customer)
            .where(
                Customer.id == customer_id,
                Customer.organization_id == self.organization_id,
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
                    select(getattr(Customer, field)).where(
                        getattr(Customer, field).in_(keys.get(field, set())),
                        Customer.organization_id == self.organization_id,
                    )
                )
            )
            for field in ("document",)
        }

    def get_by_document(self, document: str) -> Customer | None:
        statement = select(Customer).where(
            Customer.document == document,
            Customer.organization_id == self.organization_id,
        )
        return self.db.scalar(statement)

    def add(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        self.db.refresh(customer)
        return customer

    def update(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        self.db.refresh(customer)
        return customer
