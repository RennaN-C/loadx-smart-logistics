import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> Sequence[Customer]:
        statement = select(Customer).order_by(Customer.created_at.desc(), Customer.name.asc())
        return self.db.scalars(statement).all()

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
