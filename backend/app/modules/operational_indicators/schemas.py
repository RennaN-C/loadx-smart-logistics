from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FleetIndicatorsRead(BaseModel):
    period: Literal["CURRENT_SNAPSHOT"]
    total: int = Field(ge=0)
    active: int = Field(ge=0)
    inactive: int = Field(ge=0)
    available: int = Field(ge=0)
    unavailable: int = Field(ge=0)
    with_operation_conflict: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class TripIndicatorsRead(BaseModel):
    period: Literal["ALL_TIME"]
    total: int = Field(ge=0)
    scheduled: int = Field(ge=0)
    in_route: int = Field(ge=0)
    finished: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class DeliveryIndicatorsRead(BaseModel):
    period: Literal["ALL_TIME"]
    total: int = Field(ge=0)
    pending: int = Field(ge=0)
    in_delivery: int = Field(ge=0)
    delivered: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class OccurrenceIndicatorsRead(BaseModel):
    period: Literal["ALL_TIME"]
    total: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class OperationalIndicatorsRead(BaseModel):
    fleet: FleetIndicatorsRead
    trips: TripIndicatorsRead
    deliveries: DeliveryIndicatorsRead
    occurrences: OccurrenceIndicatorsRead

    model_config = ConfigDict(from_attributes=True)
