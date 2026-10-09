import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.document_validity import DocumentDates, DocumentStatus

LicenseCategory = Literal["C", "D", "E", "AC", "AD", "AE"]
LICENSE_CATEGORIES = frozenset({"C", "D", "E", "AC", "AD", "AE"})


class DocumentTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=120)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DocumentTypeRead(DocumentTypeCreate):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(DocumentDates):
    document_type_id: uuid.UUID
    reference: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=8)
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class DocumentRead(DocumentCreate):
    id: uuid.UUID
    driver_id: uuid.UUID
    superseded_at: datetime | None
    created_at: datetime
    status: DocumentStatus
    model_config = ConfigDict(from_attributes=True)


class PolicyUpdate(BaseModel):
    required: bool = Field(strict=True)
    allowed_categories: list[LicenseCategory] = Field(
        default_factory=list, max_length=6
    )
    model_config = ConfigDict(extra="forbid")

    @field_validator("allowed_categories")
    @classmethod
    def unique_categories(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("allowed_categories must be unique")
        return sorted(value)


class PolicyRead(PolicyUpdate):
    id: uuid.UUID
    driver_id: uuid.UUID
    document_type_id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)
