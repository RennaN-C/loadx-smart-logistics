import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TruckBase(BaseModel):
    plate: str = Field(min_length=1, max_length=16)
    model: str = Field(min_length=1, max_length=120)
    internal_width_cm: int = Field(gt=0)
    internal_height_cm: int = Field(gt=0)
    internal_length_cm: int = Field(gt=0)
    max_weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        return value.upper()


class TruckCreate(TruckBase):
    pass


class TruckUpdate(BaseModel):
    plate: str | None = Field(default=None, min_length=1, max_length=16)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    internal_width_cm: int | None = Field(default=None, gt=0)
    internal_height_cm: int | None = Field(default=None, gt=0)
    internal_length_cm: int | None = Field(default=None, gt=0)
    max_weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    active: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()


class TruckRead(TruckBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
