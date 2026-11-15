import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "id", name="uq_customers__organization_id"
        ),
        UniqueConstraint(
            "organization_id", "document", name="uq_customers__organization_document"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        default=lambda: LEGACY_ORGANIZATION_ID,
        server_default=text("'00000000-0000-4000-8000-000000000301'"),
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    document: Mapped[str] = mapped_column(String(32), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_customer_addresses__organization_customer",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_customer_addresses__organization_id"
        ),
        UniqueConstraint(
            "id", "customer_id", name="uq_customer_addresses__id_customer"
        ),
        CheckConstraint("NOT is_primary OR active", name="primary_active"),
        Index(
            "uq_customer_addresses__primary",
            "organization_id",
            "customer_id",
            unique=True,
            postgresql_where=text("is_primary"),
            sqlite_where=text("is_primary"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        default=lambda: LEGACY_ORGANIZATION_ID,
        server_default=text("'00000000-0000-4000-8000-000000000301'"),
    )
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="Principal")
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(8))
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
