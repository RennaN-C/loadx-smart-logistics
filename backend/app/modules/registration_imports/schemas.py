import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

MAX_IMPORT_BYTES = 1024 * 1024
MAX_IMPORT_ROWS = 1000
MAX_IMPORT_CELL = 4096
MAX_IMPORT_BASE64 = 4 * ((MAX_IMPORT_BYTES + 2) // 3)
ImportEntity = Literal["customers", "products", "trucks", "drivers"]


class ImportFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_name: str = Field(min_length=1, max_length=160)
    content_base64: str = Field(min_length=1, max_length=MAX_IMPORT_BASE64, repr=False)


class ImportConfirm(ImportFile):
    event_id: uuid.UUID
    preview_sha256: str = Field(pattern="^[0-9a-f]{64}$")


class ImportRowError(BaseModel):
    line: int = Field(ge=0)
    field: str
    code: str
    message: str


class ImportPreviewRow(BaseModel):
    line: int
    data: dict[str, JsonValue]


class ImportPreview(BaseModel):
    entity_type: ImportEntity
    sha256: str
    row_count: int
    valid_count: int
    can_confirm: bool
    errors: list[ImportRowError]
    rows: list[ImportPreviewRow]


class ImportCreatedRecord(BaseModel):
    line: int
    id: uuid.UUID


class ImportListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entity_type: ImportEntity
    recorded_by: uuid.UUID
    recorded_at: datetime
    sha256: str
    status: Literal["COMPLETED", "REJECTED"]
    row_count: int
    created_count: int
    rejected_count: int


class ImportRead(ImportListRead):
    errors: list[ImportRowError]
    records: list[ImportCreatedRecord]
