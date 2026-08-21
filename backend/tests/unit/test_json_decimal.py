import json
from decimal import Decimal

import pytest
from pydantic import BaseModel, Field, ValidationError

from app.core.json_decimal import JsonDecimal


class DecimalContract(BaseModel):
    value: JsonDecimal = Field(gt=0, max_digits=15, decimal_places=3)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (12, Decimal(12)),
        (12.5, Decimal("12.5")),
        (Decimal("12.500"), Decimal("12.500")),
    ],
)
def test_json_decimal_preserves_decimal_in_python_and_serializes_as_number(
    value: float | Decimal,
    expected: Decimal,
) -> None:
    contract = DecimalContract(value=value)

    assert contract.value == expected
    assert isinstance(contract.value, Decimal)
    serialized_value = json.loads(contract.model_dump_json())["value"]
    assert serialized_value == float(expected)
    assert isinstance(serialized_value, float)


@pytest.mark.parametrize(
    "value",
    ["12.500", True, None, float("inf"), float("nan"), Decimal("Infinity")],
)
def test_json_decimal_rejects_non_numeric_or_non_finite_values(value: object) -> None:
    with pytest.raises(ValidationError):
        DecimalContract(value=value)  # type: ignore[arg-type]


def test_json_decimal_openapi_schema_is_numeric_in_both_modes() -> None:
    validation_schema = DecimalContract.model_json_schema(mode="validation")
    serialization_schema = DecimalContract.model_json_schema(mode="serialization")

    assert validation_schema["properties"]["value"]["type"] == "number"
    assert serialization_schema["properties"]["value"]["type"] == "number"
