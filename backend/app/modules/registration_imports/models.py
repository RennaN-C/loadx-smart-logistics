import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

IMPORT_CONSTRAINTS = {
    "entity_allowed": "entity_type IN ('customers','products','trucks','drivers')",
    "hash_valid": "sha256 ~ '^[0-9a-f]{64}$' AND fingerprint ~ '^[0-9a-f]{64}$'",
    "counts_allowed": "row_count BETWEEN 0 AND 1000 AND created_count BETWEEN 0 AND row_count AND rejected_count BETWEEN 0 AND row_count",
    "result_arrays": "jsonb_typeof(errors) = 'array' AND jsonb_typeof(records) = 'array'",
    "result_consistent": "(status='PROCESSING' AND created_count=0 AND rejected_count=0 AND jsonb_array_length(errors)=0 AND jsonb_array_length(records)=0) OR (status='COMPLETED' AND row_count>0 AND created_count=row_count AND rejected_count=0 AND jsonb_array_length(errors)=0 AND jsonb_array_length(records)=row_count) OR (status='REJECTED' AND created_count=0 AND rejected_count=row_count AND jsonb_array_length(errors)>0 AND jsonb_array_length(records)=0)",
}


class RegistrationImport(Base):
    __tablename__ = "registration_imports"
    __table_args__ = (
        UniqueConstraint("recorded_by", "event_id"),
        Index(
            "ix_registration_imports__entity_recorded",
            "entity_type",
            "recorded_at",
            "id",
        ),
        Index("ix_registration_imports__actor", "recorded_by"),
        *(CheckConstraint(sql, name=name) for name, sql in IMPORT_CONSTRAINTS.items()),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="PROCESSING"
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    rejected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    errors: Mapped[list[dict]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, server_default="[]"
    )
    records: Mapped[list[dict]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, server_default="[]"
    )
