import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class StatusHistory(Base):
    __tablename__ = "status_history"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('ORDER', 'LOAD_PLAN', 'TRIP', 'DELIVERY', 'LOAD_DISTRIBUTION', 'LOAD_DISTRIBUTION_PART')",
            name="entity_type_allowed",
        ),
        Index("ix_status_history__entity", "entity_type", "entity_id"),
        Index("ix_status_history__created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(32))
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('USER_CREATED', 'USER_UPDATED', 'RECORD_ARCHIVED', 'RECORD_REACTIVATED', 'CUSTOMER_ADDRESS_CREATED', 'CUSTOMER_ADDRESS_UPDATED', 'CUSTOMER_ADDRESS_ARCHIVED', 'CUSTOMER_ADDRESS_REACTIVATED', 'MAINTENANCE_CREATED', 'MAINTENANCE_CLOSED', 'TRUCK_ODOMETER_UPDATED')",
            name="event_type_allowed",
        ),
        CheckConstraint(
            "entity_type IN ('USER', 'CUSTOMER', 'PRODUCT', 'TRUCK', 'DRIVER', 'CUSTOMER_ADDRESS', 'TRUCK_MAINTENANCE')",
            name="entity_type_allowed",
        ),
        Index("ix_audit_events__entity", "entity_type", "entity_id"),
        Index("ix_audit_events__actor_id", "actor_id"),
        Index("ix_audit_events__created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_fields: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
