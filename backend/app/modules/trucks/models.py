import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Truck(Base):
    __tablename__ = "trucks"
    __table_args__ = (
        CheckConstraint(
            "internal_width_cm > 0 AND internal_height_cm > 0 AND internal_length_cm > 0",
            name="dimensions_positive",
        ),
        CheckConstraint("max_weight_kg > 0", name="max_weight_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    plate: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    internal_width_cm: Mapped[int] = mapped_column(nullable=False)
    internal_height_cm: Mapped[int] = mapped_column(nullable=False)
    internal_length_cm: Mapped[int] = mapped_column(nullable=False)
    max_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
