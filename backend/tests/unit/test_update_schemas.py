import pytest
from pydantic import BaseModel, ValidationError

from app.modules.customers.schemas import CustomerUpdate
from app.modules.drivers.schemas import DriverUpdate
from app.modules.orders.schemas import OrderUpdate
from app.modules.products.schemas import ProductUpdate
from app.modules.trucks.schemas import TruckUpdate
from app.modules.users.schemas import UserUpdate

UPDATE_SCHEMAS = [
    UserUpdate,
    CustomerUpdate,
    DriverUpdate,
    ProductUpdate,
    TruckUpdate,
    OrderUpdate,
]

REQUIRED_UPDATE_FIELDS = [
    (UserUpdate, "name"),
    (UserUpdate, "email"),
    (UserUpdate, "password"),
    (UserUpdate, "role"),
    (UserUpdate, "active"),
    (CustomerUpdate, "name"),
    (CustomerUpdate, "document"),
    (CustomerUpdate, "address"),
    (CustomerUpdate, "city"),
    (CustomerUpdate, "state"),
    (DriverUpdate, "name"),
    (DriverUpdate, "document"),
    (DriverUpdate, "phone"),
    (DriverUpdate, "license_number"),
    (DriverUpdate, "active"),
    (ProductUpdate, "code"),
    (ProductUpdate, "name"),
    (ProductUpdate, "width_cm"),
    (ProductUpdate, "height_cm"),
    (ProductUpdate, "length_cm"),
    (ProductUpdate, "weight_kg"),
    (ProductUpdate, "fragile"),
    (ProductUpdate, "stackable"),
    (ProductUpdate, "rotation_allowed"),
    (TruckUpdate, "plate"),
    (TruckUpdate, "model"),
    (TruckUpdate, "internal_width_cm"),
    (TruckUpdate, "internal_height_cm"),
    (TruckUpdate, "internal_length_cm"),
    (TruckUpdate, "max_weight_kg"),
    (TruckUpdate, "active"),
    (OrderUpdate, "customer_id"),
    (OrderUpdate, "status"),
    (OrderUpdate, "priority"),
    (OrderUpdate, "delivery_address"),
    (OrderUpdate, "items"),
]

NULLABLE_UPDATE_FIELDS = [
    (UserUpdate, "driver_id"),
    (CustomerUpdate, "phone"),
    (CustomerUpdate, "notes"),
    (DriverUpdate, "license_category"),
    (ProductUpdate, "description"),
    (OrderUpdate, "expected_delivery_at"),
]


@pytest.mark.parametrize("schema", UPDATE_SCHEMAS)
def test_update_schema_keeps_omitted_fields_unset(schema: type[BaseModel]) -> None:
    update = schema.model_validate({})

    assert update.model_fields_set == set()


@pytest.mark.parametrize(("schema", "field_name"), REQUIRED_UPDATE_FIELDS)
def test_update_schema_rejects_explicit_null_for_required_field(
    schema: type[BaseModel],
    field_name: str,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        schema.model_validate({field_name: None})

    assert exc_info.value.errors()[0]["loc"] == (field_name,)


@pytest.mark.parametrize(("schema", "field_name"), NULLABLE_UPDATE_FIELDS)
def test_update_schema_accepts_explicit_null_for_nullable_field(
    schema: type[BaseModel],
    field_name: str,
) -> None:
    update = schema.model_validate({field_name: None})

    assert update.model_dump(exclude_unset=True) == {field_name: None}
    assert field_name in update.model_fields_set
