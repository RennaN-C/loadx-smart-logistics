import uuid
from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.modules.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from app.modules.drivers.schemas import DriverCreate, DriverRead, DriverUpdate

CUSTOMER_INPUT = {
    "name": "Cliente fictício",
    "document": "123.456.789-09",
    "phone": "(11) 3000-0000",
    "address": "Rua de Teste, 1",
    "city": "Cidade de Teste",
    "state": "SP",
}
DRIVER_INPUT = {
    "name": "Motorista fictício",
    "document": "987.654.321-00",
    "phone": "(11) 90000-0000",
    "license_number": " 12345678900 ",
}


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ("123.456.789-09", "12345678909"),
        ("00.000.000/0001-91", "00000000000191"),
    ],
)
def test_customer_create_normalizes_document_and_phone(
    document: str, expected: str
) -> None:
    customer = CustomerCreate.model_validate({**CUSTOMER_INPUT, "document": document})

    assert customer.model_dump()["document"] == expected
    assert customer.model_dump()["phone"] == "1130000000"


def test_customer_update_normalizes_only_supplied_fields() -> None:
    update = CustomerUpdate(document="00.000.000/0002-72", phone="(11) 90000-0000")

    assert update.model_dump(exclude_unset=True) == {
        "document": "00000000000272",
        "phone": "11900000000",
    }


def test_driver_create_normalizes_cpf_phone_and_cnh() -> None:
    driver = DriverCreate.model_validate(DRIVER_INPUT)

    assert driver.document == "98765432100"
    assert driver.phone == "11900000000"
    assert driver.license_number == "12345678900"


def test_driver_update_normalizes_only_supplied_fields() -> None:
    update = DriverUpdate(
        document="123.456.789-09",
        phone="(11) 3000-0000",
        license_number=" 98765432109 ",
    )

    assert update.model_dump(exclude_unset=True) == {
        "document": "12345678909",
        "phone": "1130000000",
        "license_number": "98765432109",
    }


@pytest.mark.parametrize(
    ("create_schema", "update_schema", "base_input", "field", "invalid_value"),
    [
        (CustomerCreate, CustomerUpdate, CUSTOMER_INPUT, "document", "12345678908"),
        (CustomerCreate, CustomerUpdate, CUSTOMER_INPUT, "document", "00000000000190"),
        (CustomerCreate, CustomerUpdate, CUSTOMER_INPUT, "phone", "11800000000"),
        (CustomerCreate, CustomerUpdate, CUSTOMER_INPUT, "phone", ""),
        (DriverCreate, DriverUpdate, DRIVER_INPUT, "document", "12345678908"),
        (DriverCreate, DriverUpdate, DRIVER_INPUT, "document", "00000000000191"),
        (DriverCreate, DriverUpdate, DRIVER_INPUT, "phone", "0130000000"),
        (DriverCreate, DriverUpdate, DRIVER_INPUT, "license_number", "12345678901"),
    ],
)
def test_create_and_update_reject_invalid_registration_fields(
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    base_input: dict[str, str],
    field: str,
    invalid_value: str,
) -> None:
    for schema, payload in (
        (create_schema, {**base_input, field: invalid_value}),
        (update_schema, {field: invalid_value}),
    ):
        with pytest.raises(ValidationError) as exc_info:
            schema.model_validate(payload)

        assert exc_info.value.errors()[0]["loc"] == (field,)


def test_customer_phone_can_be_omitted_or_explicitly_null() -> None:
    payload_without_phone = {
        field: value for field, value in CUSTOMER_INPUT.items() if field != "phone"
    }

    assert CustomerCreate.model_validate(payload_without_phone).phone is None
    assert (
        CustomerCreate.model_validate({**CUSTOMER_INPUT, "phone": None}).phone is None
    )
    assert CustomerUpdate().model_dump(exclude_unset=True) == {}
    assert CustomerUpdate(phone=None).model_dump(exclude_unset=True) == {"phone": None}


def test_driver_phone_is_required_on_create() -> None:
    payload_without_phone = {
        field: value for field, value in DRIVER_INPUT.items() if field != "phone"
    }

    with pytest.raises(ValidationError) as exc_info:
        DriverCreate.model_validate(payload_without_phone)

    assert exc_info.value.errors()[0]["loc"] == ("phone",)
    assert exc_info.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize("field", ["document", "phone", "license_number"])
def test_driver_registration_fields_allow_omission_but_not_null(field: str) -> None:
    assert DriverUpdate().model_dump(exclude_unset=True) == {}

    for schema, payload in (
        (DriverCreate, {**DRIVER_INPUT, field: None}),
        (DriverUpdate, {field: None}),
    ):
        with pytest.raises(ValidationError) as exc_info:
            schema.model_validate(payload)

        assert exc_info.value.errors()[0]["loc"] == (field,)


def test_customer_document_allows_omission_on_update_but_not_null() -> None:
    assert CustomerUpdate().model_dump(exclude_unset=True) == {}

    for schema, payload in (
        (CustomerCreate, {**CUSTOMER_INPUT, "document": None}),
        (CustomerUpdate, {"document": None}),
    ):
        with pytest.raises(ValidationError) as exc_info:
            schema.model_validate(payload)

        assert exc_info.value.errors()[0]["loc"] == ("document",)


def test_customer_read_preserves_legacy_registration_values() -> None:
    customer = CustomerRead.model_validate(
        {
            **CUSTOMER_INPUT,
            "id": uuid.uuid4(),
            "created_at": datetime.now(UTC),
            "document": "documento-legado",
            "phone": "5500000000000",
        }
    )

    assert customer.document == "documento-legado"
    assert customer.phone == "5500000000000"


def test_driver_read_preserves_legacy_registration_values() -> None:
    driver = DriverRead.model_validate(
        {
            **DRIVER_INPUT,
            "id": uuid.uuid4(),
            "created_at": datetime.now(UTC),
            "document": "00000000000",
            "phone": "5500000000000",
            "license_number": "CNH0001",
        }
    )

    assert driver.document == "00000000000"
    assert driver.phone == "5500000000000"
    assert driver.license_number == "CNH0001"
