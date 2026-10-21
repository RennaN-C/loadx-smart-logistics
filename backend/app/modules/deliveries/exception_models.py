"""Append-only attempts ledger; no original trip, delivery or receipt is rewritten."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class DeliveryException(Base):
    __tablename__ = "delivery_exceptions"
    __table_args__ = (
        CheckConstraint("code IN ('CUSTOMER_ABSENT', 'REFUSED', 'DAMAGED', 'OPERATIONAL_FAILURE', 'RESCHEDULED', 'RESUMED')", name="code_allowed"),
        UniqueConstraint("delivery_id", "idempotency_key", name="uq_delivery_exceptions__delivery_request"),
        Index("ix_delivery_exceptions__delivery_created", "delivery_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deliveries.id", ondelete="RESTRICT"), nullable=False)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
