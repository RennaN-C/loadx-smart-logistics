import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.modules.customers.schemas import CustomerCreate
from app.modules.customers.service import CustomerService
from app.modules.drivers.schemas import DriverCreate
from app.modules.drivers.service import DriverService
from app.modules.products.schemas import ProductCreate
from app.modules.products.service import ProductService
from app.modules.registration_imports.schemas import ImportEntity
from app.modules.trucks.schemas import TruckCreate
from app.modules.trucks.service import TruckService


class CreatedRegistration(Protocol):
    id: uuid.UUID


@dataclass(frozen=True, slots=True)
class RegistrationAdapter:
    schema: type[BaseModel]
    unique_fields: tuple[str, ...]
    existing: Callable[[dict[str, set[str]]], dict[str, set[str]]]
    stage: Callable[[BaseModel, uuid.UUID], CreatedRegistration]


def registration_adapter(db: Session, entity: ImportEntity) -> RegistrationAdapter:
    if entity == "customers":
        service = CustomerService(db)
        return RegistrationAdapter(
            CustomerCreate,
            ("document",),
            service.existing_registration_keys,
            lambda data, actor: service.stage_create_customer(
                cast(CustomerCreate, data), changed_by=actor
            ),
        )
    if entity == "products":
        products = ProductService(db)
        return RegistrationAdapter(
            ProductCreate,
            ("code",),
            products.existing_registration_keys,
            lambda data, _actor: products.stage_create_product(
                cast(ProductCreate, data)
            ),
        )
    if entity == "trucks":
        trucks = TruckService(db)
        return RegistrationAdapter(
            TruckCreate,
            ("plate",),
            trucks.existing_registration_keys,
            lambda data, _actor: trucks.stage_create_truck(cast(TruckCreate, data)),
        )
    drivers = DriverService(db)
    return RegistrationAdapter(
        DriverCreate,
        ("document", "license_number"),
        drivers.existing_registration_keys,
        lambda data, actor: drivers.stage_create_driver(
            cast(DriverCreate, data), changed_by=actor
        ),
    )
