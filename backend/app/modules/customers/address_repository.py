import uuid
from collections.abc import Sequence

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.customers.models import CustomerAddress


class CustomerAddressRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        customer_id: uuid.UUID,
        pagination: PaginationParams,
        *,
        active: bool | None,
    ) -> PageResult[CustomerAddress]:
        filters = [CustomerAddress.customer_id == customer_id]
        if active is not None:
            filters.append(CustomerAddress.active.is_(active))
        direction = asc if pagination.sort_order == "asc" else desc
        statement = (
            select(CustomerAddress)
            .where(*filters)
            .order_by(
                direction(CustomerAddress.created_at), direction(CustomerAddress.id)
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        total = (
            self.db.scalar(
                select(func.count()).select_from(CustomerAddress).where(*filters)
            )
            or 0
        )
        return PageResult.create(self.db.scalars(statement).all(), pagination, total)

    def all(self, customer_id: uuid.UUID) -> Sequence[CustomerAddress]:
        statement = (
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .order_by(CustomerAddress.created_at, CustomerAddress.id)
            .execution_options(populate_existing=True)
        )
        return self.db.scalars(statement).all()

    def get_for_update(
        self, customer_id: uuid.UUID, address_id: uuid.UUID
    ) -> CustomerAddress | None:
        return self.db.scalar(
            select(CustomerAddress)
            .where(
                CustomerAddress.id == address_id,
                CustomerAddress.customer_id == customer_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def add(self, address: CustomerAddress) -> CustomerAddress:
        self.db.add(address)
        self.db.flush()
        return address
