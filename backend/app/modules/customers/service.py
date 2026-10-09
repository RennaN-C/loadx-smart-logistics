import uuid
from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.pagination import PageResult, PaginationParams
from app.database.integrity import get_integrity_constraint_name
from app.modules.customers.address_service import CustomerAddressService
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import CustomerCreate, CustomerUpdate
from app.shared.record_lifecycle import stage_lifecycle_event, validate_reactivation


class CustomerNotFoundError(Exception):
    pass


class CustomerDocumentAlreadyExistsError(Exception):
    pass


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CustomerRepository(db)

    def list_customers(
        self, pagination: PaginationParams, *, active: bool | None = None
    ) -> PageResult[Customer]:
        return self.repository.list(pagination, active=active)

    def get_customer(
        self, customer_id: uuid.UUID, *, for_update: bool = False
    ) -> Customer:
        customer = (
            self.repository.get_for_update(customer_id)
            if for_update
            else self.repository.get(customer_id)
        )
        if customer is None:
            raise CustomerNotFoundError
        return customer

    def create_customer(
        self, data: CustomerCreate, *, changed_by: uuid.UUID | None = None
    ) -> Customer:
        return self._persist(
            lambda: self.stage_create_customer(data, changed_by=changed_by)
        )

    def stage_create_customer(
        self, data: CustomerCreate, *, changed_by: uuid.UUID | None = None
    ) -> Customer:
        """Stage the same manual creation rules in an outer atomic transaction."""
        if self.repository.get_by_document(data.document) is not None:
            raise CustomerDocumentAlreadyExistsError
        customer = self.repository.add(Customer(**data.model_dump()))
        CustomerAddressService(self.db).stage_legacy_address(
            customer, changed_by=changed_by
        )
        return customer

    def existing_registration_keys(
        self, keys: dict[str, set[str]]
    ) -> dict[str, set[str]]:
        """Public batched uniqueness boundary, including archived registrations."""
        return self.repository.existing_registration_keys(keys)

    def update_customer(
        self,
        customer_id: uuid.UUID,
        data: CustomerUpdate,
        *,
        changed_by: uuid.UUID | None = None,
    ) -> Customer:
        customer = self.repository.get_for_update(customer_id)
        if customer is None:
            raise CustomerNotFoundError
        old_active = customer.active
        update_data = data.model_dump(exclude_unset=True)

        new_document = update_data.get("document")
        if new_document is not None and new_document != customer.document:
            existing_customer = self.repository.get_by_document(new_document)
            if existing_customer is not None and existing_customer.id != customer.id:
                raise CustomerDocumentAlreadyExistsError

        for field_name, value in update_data.items():
            setattr(customer, field_name, value)

        def stage_update() -> Customer:
            if not old_active and customer.active:
                validate_reactivation(CustomerCreate, customer)
            self.repository.update(customer)
            if {"address", "city", "state"}.intersection(update_data):
                CustomerAddressService(self.db).stage_legacy_address(
                    customer, changed_by=changed_by
                )
            stage_lifecycle_event(
                self.db,
                entity_type="CUSTOMER",
                entity_id=customer.id,
                old_active=old_active,
                new_active=customer.active,
                changed_by=changed_by,
            )
            return customer

        return self._persist(stage_update)

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
        except Exception:
            self.db.rollback()
            raise
        return customer
