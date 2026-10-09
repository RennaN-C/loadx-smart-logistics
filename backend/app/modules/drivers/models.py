import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    document: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    license_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    license_category: Mapped[str | None] = mapped_column(String(8))
    license_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


CNH_TYPE_ID = uuid.UUID("00000000-0000-4000-8000-000000000102")


class DriverDocumentType(Base):
    __tablename__ = "driver_document_types"
    __table_args__ = (
        CheckConstraint(
            "length(trim(code)) > 0 AND length(trim(name)) > 0", name="labels_required"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class DriverDocument(Base):
    __tablename__ = "driver_documents"
    __table_args__ = (
        CheckConstraint("length(trim(reference)) > 0", name="reference_required"),
        CheckConstraint(
            "issued_at IS NULL OR expires_at IS NULL OR expires_at > issued_at",
            name="period_valid",
        ),
        Index(
            "uq_driver_documents__current_type",
            "driver_id",
            "document_type_id",
            unique=True,
            postgresql_where=text("superseded_at IS NULL"),
            sqlite_where=text("superseded_at IS NULL"),
        ),
        Index("ix_driver_documents__driver_created", "driver_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False
    )
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("driver_document_types.id", ondelete="RESTRICT"), nullable=False
    )
    legacy_backfill: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(8))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DriverDocumentPolicy(Base):
    __tablename__ = "driver_document_policies"
    __table_args__ = (
        UniqueConstraint(
            "driver_id",
            "document_type_id",
            name="uq_driver_document_policies__driver_type",
        ),
        CheckConstraint(
            "jsonb_typeof(allowed_categories) = 'array'", name="categories_array"
        ).ddl_if(dialect="postgresql"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False
    )
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("driver_document_types.id", ondelete="RESTRICT"), nullable=False
    )
    required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    allowed_categories: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=list,
        server_default="[]",
    )
