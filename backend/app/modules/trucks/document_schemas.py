import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.document_validity import DocumentDates, DocumentStatus, document_status

__all__ = [
    "DocumentCreate",
    "DocumentKind",
    "DocumentRead",
    "DocumentStatus",
    "PolicyRead",
    "PolicyUpdate",
    "document_status",
]

DocumentKind = Literal["CRLV", "LICENSING", "INSURANCE"]


class DocumentCreate(DocumentDates):
    kind: DocumentKind
    reference: str = Field(min_length=1, max_length=120)
    file_reference: uuid.UUID | None = None
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class DocumentRead(DocumentCreate):
    id: uuid.UUID
    truck_id: uuid.UUID
    superseded_at: datetime | None
    created_at: datetime
    status: DocumentStatus
    model_config = ConfigDict(from_attributes=True)


class PolicyUpdate(BaseModel):
    required: bool = Field(strict=True)
    model_config = ConfigDict(extra="forbid")


class PolicyRead(PolicyUpdate):
    id: uuid.UUID
    truck_id: uuid.UUID
    kind: DocumentKind
    model_config = ConfigDict(from_attributes=True)
