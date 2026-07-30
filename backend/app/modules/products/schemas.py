import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    width_cm: int = Field(gt=0)
    height_cm: int = Field(gt=0)
    length_cm: int = Field(gt=0)
    weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    fragile: bool = False
    stackable: bool = True
    rotation_allowed: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    width_cm: int | None = Field(default=None, gt=0)
    height_cm: int | None = Field(default=None, gt=0)
    length_cm: int | None = Field(default=None, gt=0)
    weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    fragile: bool | None = None
    stackable: bool | None = None
    rotation_allowed: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.upper()


class ProductRead(ProductBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)
