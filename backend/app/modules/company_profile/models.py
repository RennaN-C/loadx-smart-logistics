import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

PROFILE_ID = uuid.UUID("00000000-0000-0000-0000-000000000091")


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (
        CheckConstraint(f"id = '{PROFILE_ID}'", name="singleton"),
        CheckConstraint(
            "length(trim(legal_name)) > 0 AND length(trim(display_name)) > 0",
            name="names_not_empty",
        ),
        CheckConstraint("cnpj IS NULL OR cnpj ~ '^[0-9]{14}$'", name="cnpj_format"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=lambda: PROFILE_ID
    )
    legal_name: Mapped[str] = mapped_column(String(160))
    display_name: Mapped[str] = mapped_column(String(160))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    phone: Mapped[str | None] = mapped_column(String(11))
    email: Mapped[str | None] = mapped_column(String(255))
    logo_reference: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
