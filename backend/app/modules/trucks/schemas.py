import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.json_decimal import JsonDecimal
from app.modules.trucks.maintenance_schemas import Kilometers


class TruckBase(BaseModel):
    plate: str = Field(min_length=1, max_length=16)
    model: str = Field(min_length=1, max_length=120)
    internal_width_cm: int = Field(gt=0)
    internal_height_cm: int = Field(gt=0)
    internal_length_cm: int = Field(gt=0)
    max_weight_kg: JsonDecimal = Field(gt=0, max_digits=10, decimal_places=2)
    odometer_km: Kilometers | None = None
    active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        return value.upper()


class TruckCreate(TruckBase):
    pass


class TruckUpdate(BaseModel):
    odometer_km: Kilometers | None = None
    plate: str | None = Field(default=None, min_length=1, max_length=16)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    internal_width_cm: int | None = Field(default=None, gt=0)
    internal_height_cm: int | None = Field(default=None, gt=0)
    internal_length_cm: int | None = Field(default=None, gt=0)
    max_weight_kg: JsonDecimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2
    )
    active: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "odometer_km",
        "plate",
        "model",
        "internal_width_cm",
        "internal_height_cm",
        "internal_length_cm",
        "max_weight_kg",
        "active",
        mode="before",
    )
    @classmethod
    def reject_null_required_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("field must not be null")
        return value

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()


class TruckRead(TruckBase):
    id: uuid.UUID
    created_at: datetime
    next_service_at: datetime | None = None
    next_service_km: int | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class TruckOperationalStatusRead(BaseModel):
    id: uuid.UUID
    plate: str
    model: str
    active: bool
    has_operation_conflict: bool
    has_document_conflict: bool
    has_maintenance_conflict: bool
    available: bool

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
