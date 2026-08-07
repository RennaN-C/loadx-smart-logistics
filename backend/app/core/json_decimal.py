from decimal import Decimal
from math import isfinite
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer
from pydantic_core import PydanticCustomError


def _require_json_number(value: object) -> object:
    """Reject ambiguous JSON strings while allowing internal Decimal values."""

    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise PydanticCustomError("json_number_type", "value must be a JSON number")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("value must be finite")
    if isinstance(value, Decimal) and not value.is_finite():
        raise ValueError("value must be finite")
    return value


def _serialize_json_decimal(value: Decimal) -> float:
    return float(value)


JsonDecimal = Annotated[
    Decimal,
    BeforeValidator(_require_json_number, json_schema_input_type=float),
    PlainSerializer(_serialize_json_decimal, return_type=float, when_used="json"),
]
