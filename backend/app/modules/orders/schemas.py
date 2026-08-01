import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

ORDER_STATUS_VALUES = {
    "DRAFT",
    "READY",
    "PLANNED",
    "IN_TRANSIT",
    "DELIVERED",
    "CANCELED",
}


def normalize_required_upper(value: str) -> str:
    return value.upper()


def normalize_optional_upper(value: str | None) -> str | None:
    if value is None:
        return None
    return value.upper()


def normalize_optional_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("expected_delivery_at must include timezone")
    return value.astimezone(timezone.utc)


def validate_order_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized_value = value.upper()
    if normalized_value not in ORDER_STATUS_VALUES:
        allowed_values = ", ".join(sorted(ORDER_STATUS_VALUES))
        raise ValueError(f"status must be one of: {allowed_values}")
    return normalized_value


class OrderItemBase(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    delivery_sequence: int = Field(gt=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemRead(OrderItemBase):
    id: uuid.UUID
    order_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    customer_id: uuid.UUID
    priority: str = Field(min_length=1, max_length=32)
    delivery_address: str = Field(min_length=1, max_length=255)
    expected_delivery_at: datetime | None = None
    items: list[OrderItemCreate] = Field(min_length=1)

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        return normalize_required_upper(value)

    @field_validator("expected_delivery_at")
    @classmethod
    def normalize_expected_delivery_at(cls, value: datetime | None) -> datetime | None:
        return normalize_optional_utc(value)


class OrderUpdate(BaseModel):
    customer_id: uuid.UUID | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)
    priority: str | None = Field(default=None, min_length=1, max_length=32)
    delivery_address: str | None = Field(default=None, min_length=1, max_length=255)
    expected_delivery_at: datetime | None = None
    items: list[OrderItemCreate] | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "customer_id",
        "status",
        "priority",
        "delivery_address",
        "items",
        mode="before",
    )
    @classmethod
    def reject_null_required_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("field must not be null")
        return value

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        return validate_order_status(value)

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, value: str | None) -> str | None:
        return normalize_optional_upper(value)

    @field_validator("expected_delivery_at")
    @classmethod
    def normalize_expected_delivery_at(cls, value: datetime | None) -> datetime | None:
        return normalize_optional_utc(value)

    @field_validator("items")
    @classmethod
    def validate_items(
        cls, value: list[OrderItemCreate] | None
    ) -> list[OrderItemCreate] | None:
        if value is not None and len(value) == 0:
            raise ValueError("items must have at least one item")
        return value


class OrderRead(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    priority: str
    delivery_address: str
    expected_delivery_at: datetime | None
    created_at: datetime
    items: list[OrderItemRead]

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
