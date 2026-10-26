import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.deliveries.evidence_schemas import MAX_BASE64_LENGTH

AttachmentResource = Literal["orders", "trips", "deliveries", "occurrences"]


class AttachmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: uuid.UUID
    content_base64: str = Field(min_length=1, max_length=MAX_BASE64_LENGTH, repr=False)


class AttachmentRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    resource_type: AttachmentResource
    resource_id: uuid.UUID
    media_type: Literal["image/png", "image/jpeg"]
    size_bytes: int
    sha256: str
    status: Literal["ACTIVE", "REVOKED"]
    recorded_by: uuid.UUID
    recorded_at: datetime
    revoked_by: uuid.UUID | None
    revoked_at: datetime | None
