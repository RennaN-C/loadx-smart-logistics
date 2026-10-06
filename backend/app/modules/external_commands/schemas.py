import uuid
from datetime import timedelta
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class CommandName(StrEnum):
    START_TRIP = "START_TRIP"
    START_DELIVERY = "START_DELIVERY"
    FINISH_DELIVERY = "FINISH_DELIVERY"


class ExternalCommandEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1]
    event_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    subject: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    command: CommandName
    target_id: uuid.UUID
    issued_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def validate_lifetime(self) -> "ExternalCommandEnvelope":
        duration = self.expires_at - self.issued_at
        if not timedelta(0) < duration <= timedelta(minutes=5):
            raise ValueError("invalid command lifetime")
        return self


class ExternalCommandReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    duplicate: bool
