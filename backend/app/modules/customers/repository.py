import uuid

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.modules.customers.models import Customer


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, pagination: PaginationParams) -> PageResult[Customer]:
        direction = asc if pagination.sort_order == "asc" else desc
        total = self.db.scalar(select(func.count()).select_from(Customer)) or 0
        statement = (
            select(Customer)
            .order_by(direction(Customer.created_at), direction(Customer.id))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        return PageResult.create(
            self.db.scalars(statement).all(),
            pagination,
            total,
        )

    def get(self, customer_id: uuid.UUID) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def get_by_document(self, document: str) -> Customer | None:
        statement = select(Customer).where(Customer.document == document)
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
