import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PageResult, PaginationParams
from app.modules.customers.address_repository import CustomerAddressRepository
from app.modules.customers.address_schemas import (
    CustomerAddressCreate,
    CustomerAddressUpdate,
)
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.customers.repository import CustomerRepository
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.shared.record_lifecycle import ensure_record_active


class CustomerAddressService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CustomerAddressRepository(db)
        self.customers = CustomerRepository(db)

    def _customer(self, identifier: uuid.UUID, *, lock: bool = True) -> Customer:
        customer = (
            self.customers.get_for_update(identifier)
            if lock
            else self.customers.get(identifier)
        )
        if customer is None:
            raise ApiError(404, "CUSTOMER_NOT_FOUND", "Cliente não encontrado.")
        return customer

    def list_addresses(
        self,
        customer_id: uuid.UUID,
        pagination: PaginationParams,
        *,
        active: bool | None = True,
    ) -> PageResult[CustomerAddress]:
        self._customer(customer_id, lock=False)
        return self.repository.list(customer_id, pagination, active=active)

    def select_for_order(
        self, customer_id: uuid.UUID, address_id: uuid.UUID
    ) -> tuple[str, dict]:
        customer = self._customer(customer_id)
        ensure_record_active(customer, "CUSTOMER")
        address = self.repository.get_for_update(customer_id, address_id)
        if address is None:
            raise ApiError(
                422,
                "CUSTOMER_ADDRESS_INVALID",
                "Selecione um endereço pertencente ao cliente.",
                [{"field": "customer_address_id"}],
            )
        ensure_record_active(address, "CUSTOMER_ADDRESS")
        snapshot = {
            field: getattr(address, field)
            for field in ("label", "address", "city", "state", "postal_code")
        }
        snapshot["customer_address_id"] = str(address.id)
        return address.address, snapshot

    def _primary(
        self,
        customer: Customer,
        rows: Sequence[CustomerAddress],
        preferred: CustomerAddress | None = None,
    ) -> None:
        active = [row for row in rows if row.active]
        selected = (
            preferred
            if preferred is not None and preferred.active
            else next(
                (row for row in active if row.is_primary), active[0] if active else None
            )
        )
        for row in rows:
            row.is_primary = False
        # Clear the previous unique primary before setting the replacement.
        self.db.flush()
        if selected is not None:
            selected.is_primary = True
            customer.address, customer.city, customer.state = (
                selected.address,
                selected.city,
                selected.state,
            )
            self.customers.update(customer)

    def _audit(
        self,
        address: CustomerAddress,
        event: str,
        changed_fields: Sequence[str],
        actor: uuid.UUID | None,
    ) -> None:
        if actor is not None:
            AuditService(self.db).stage_administrative_event(
                AuditEventCreate(
                    event_type=event,
                    entity_type="CUSTOMER_ADDRESS",
                    entity_id=address.id,
                    actor_id=actor,
                    changed_fields=list(changed_fields),
                )
            )

    def stage_legacy_address(
        self, customer: Customer, *, changed_by: uuid.UUID | None = None
    ) -> CustomerAddress:
        rows = list(self.repository.all(customer.id))
        primary = next((row for row in rows if row.active and row.is_primary), None)
        fields = ("address", "city", "state")
        if primary is None:
            primary = CustomerAddress(
                id=uuid.uuid4(),
                customer_id=customer.id,
                label="Principal",
                active=True,
                is_primary=False,
                **{field: getattr(customer, field) for field in fields},
            )
            rows.append(primary)
            self._primary(customer, rows, primary)
            self.repository.add(primary)
            self._audit(primary, "CUSTOMER_ADDRESS_CREATED", fields, changed_by)
        else:
            changed = [
                field
                for field in fields
                if getattr(primary, field) != getattr(customer, field)
            ]
            for field in fields:
                setattr(primary, field, getattr(customer, field))
            if changed:
                primary.postal_code = None
                self.repository.add(primary)
                self._audit(
                    primary,
                    "CUSTOMER_ADDRESS_UPDATED",
                    [*changed, "postal_code"],
                    changed_by,
                )
        return primary

    def create_address(
        self,
        customer_id: uuid.UUID,
        data: CustomerAddressCreate,
        *,
        changed_by: uuid.UUID,
    ) -> CustomerAddress:
        try:
            customer = self._customer(customer_id)
            rows = list(self.repository.all(customer_id))
            address = CustomerAddress(
                id=uuid.uuid4(), customer_id=customer_id, **data.model_dump()
            )
            if address.is_primary and not address.active:
                raise ApiError(
                    409,
                    "CUSTOMER_ADDRESS_PRIMARY_INACTIVE",
                    "O endereço principal deve estar ativo.",
                )
            rows.append(address)
            self._primary(customer, rows, address if address.is_primary else None)
            self.repository.add(address)
            self._audit(
                address, "CUSTOMER_ADDRESS_CREATED", data.model_fields_set, changed_by
            )
            self.db.commit()
            self.db.refresh(address)
            return address
        except Exception:
            self.db.rollback()
            raise

    def update_address(
        self,
        customer_id: uuid.UUID,
        address_id: uuid.UUID,
        data: CustomerAddressUpdate,
        *,
        changed_by: uuid.UUID,
    ) -> CustomerAddress:
        try:
            customer = self._customer(customer_id)
            rows = list(self.repository.all(customer_id))
            address = next((row for row in rows if row.id == address_id), None)
            if address is None:
                raise ApiError(
                    404,
                    "CUSTOMER_ADDRESS_NOT_FOUND",
                    "Endereço não encontrado para este cliente.",
                )
            changes = data.model_dump(exclude_unset=True)
            old_active, old_primary = address.active, address.is_primary
            changed_fields = [
                field
                for field, value in changes.items()
                if getattr(address, field) != value
            ]
            if not changed_fields:
                self.db.commit()
                return address
            if (
                old_primary
                and changes.get("is_primary") is False
                and changes.get("active", True)
            ):
                raise ApiError(
                    409,
                    "CUSTOMER_ADDRESS_PRIMARY_REQUIRED",
                    "Marque outro endereço como principal antes de desmarcar este.",
                )
            for field, value in changes.items():
                setattr(address, field, value)
            if changes.get("is_primary") is True and not address.active:
                raise ApiError(
                    409,
                    "CUSTOMER_ADDRESS_PRIMARY_INACTIVE",
                    "O endereço principal deve estar ativo.",
                )
            self._primary(
                customer, rows, address if changes.get("is_primary") is True else None
            )
            self.repository.add(address)
            event = (
                "CUSTOMER_ADDRESS_UPDATED"
                if old_active == address.active
                else (
                    "CUSTOMER_ADDRESS_REACTIVATED"
                    if address.active
                    else "CUSTOMER_ADDRESS_ARCHIVED"
                )
            )
            self._audit(address, event, changed_fields, changed_by)
            self.db.commit()
            self.db.refresh(address)
            return address
        except Exception:
            self.db.rollback()
            raise
