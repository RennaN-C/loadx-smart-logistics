import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Uuid, func
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
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
