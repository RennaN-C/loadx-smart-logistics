import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "width_cm > 0 AND height_cm > 0 AND length_cm > 0",
            name="dimensions_positive",
        ),
        CheckConstraint("weight_kg > 0", name="weight_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    width_cm: Mapped[int] = mapped_column(nullable=False)
    height_cm: Mapped[int] = mapped_column(nullable=False)
    length_cm: Mapped[int] = mapped_column(nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    fragile: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    stackable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    rotation_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
