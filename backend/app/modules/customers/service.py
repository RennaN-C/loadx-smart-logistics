import uuid
from collections.abc import Callable, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import get_integrity_constraint_name
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import CustomerCreate, CustomerUpdate


class CustomerNotFoundError(Exception):
    pass


class CustomerDocumentAlreadyExistsError(Exception):
    pass


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CustomerRepository(db)

    def list_customers(self) -> Sequence[Customer]:
        return self.repository.list()

    def get_customer(self, customer_id: uuid.UUID) -> Customer:
        customer = self.repository.get(customer_id)
        if customer is None:
            raise CustomerNotFoundError
        return customer

    def create_customer(self, data: CustomerCreate) -> Customer:
        if self.repository.get_by_document(data.document) is not None:
            raise CustomerDocumentAlreadyExistsError

        customer = Customer(**data.model_dump())
        return self._persist(lambda: self.repository.add(customer))

    def update_customer(self, customer_id: uuid.UUID, data: CustomerUpdate) -> Customer:
        customer = self.get_customer(customer_id)
        update_data = data.model_dump(exclude_unset=True)

        new_document = update_data.get("document")
        if new_document is not None and new_document != customer.document:
            existing_customer = self.repository.get_by_document(new_document)
            if existing_customer is not None and existing_customer.id != customer.id:
                raise CustomerDocumentAlreadyExistsError

        for field_name, value in update_data.items():
            setattr(customer, field_name, value)

        return self._persist(lambda: self.repository.update(customer))

    def _persist(self, operation: Callable[[], Customer]) -> Customer:
        try:
            customer = operation()
            self.db.commit()
            self.db.refresh(customer)
        except IntegrityError as exc:
            self.db.rollback()
            if get_integrity_constraint_name(exc) == "uq_customers__document":
                raise CustomerDocumentAlreadyExistsError from exc
            raise
        return customer
