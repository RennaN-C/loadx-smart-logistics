import uuid

from pydantic import BaseModel, ConfigDict, Field


class MessageInterpretRequest(BaseModel):
    driver_phone: str = Field(min_length=1, max_length=32)
    message: str = Field(min_length=1)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class MessageInterpretResponse(BaseModel):
    intent: str | None
    confidence: float = Field(ge=0, le=1)
    allowed: bool
    action: str | None
    executed: bool = False
    confirmation: str | None = None
    trip_id: uuid.UUID | None = None
    delivery_id: uuid.UUID | None = None
