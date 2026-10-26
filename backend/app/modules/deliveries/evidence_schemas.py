import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_EVIDENCE_BYTES = 5 * 1024 * 1024
MAX_BASE64_LENGTH = 4 * ((MAX_EVIDENCE_BYTES + 2) // 3)


class DeliveryEvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: uuid.UUID
    kind: Literal["PHOTO", "SIGNATURE"]
    content_base64: str = Field(min_length=1, max_length=MAX_BASE64_LENGTH, repr=False)


class DeliveryEvidenceRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeliveryEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_id: uuid.UUID
    receipt_id: uuid.UUID
    kind: Literal["PHOTO", "SIGNATURE"]
    media_type: Literal["image/png", "image/jpeg"]
    size_bytes: int
    sha256: str
    status: Literal["ACTIVE", "REVOKED"]
    recorded_by: uuid.UUID
    recorded_at: datetime
    revoked_by: uuid.UUID | None
    revoked_at: datetime | None
