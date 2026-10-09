import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.json_decimal import JsonDecimal
from app.shared.document_validity import utc_datetime

Kilometers = Annotated[int, Field(ge=0, le=9_223_372_036_854_775_807, strict=True)]


class MaintenanceCreate(BaseModel):
    kind: Literal["PREVENTIVE", "CORRECTIVE"]
    starts_at: datetime
    ends_at: datetime | None = None
    description: str = Field(min_length=1, max_length=2000)
    workshop: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)
    cost: JsonDecimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    odometer_km: Kilometers | None = None
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("starts_at", "ends_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        return utc_datetime(value)

    @model_validator(mode="after")
    def validate_period(self) -> "MaintenanceCreate":
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class MaintenanceClose(BaseModel):
    odometer_km: Kilometers | None = None
    next_service_at: datetime | None = None
    next_service_km: Kilometers | None = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("next_service_at")
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        return utc_datetime(value)


class MaintenanceRead(MaintenanceCreate):
    id: uuid.UUID
    truck_id: uuid.UUID
    completion_odometer_km: int | None
    next_service_at: datetime | None
    next_service_km: int | None
    closed_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
