"""Durable channel work; domain facts and personal receipts remain separate."""

import uuid
from datetime import datetime

from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

STATES = ("PENDING", "PROCESSING", "SUCCEEDED", "RETRYABLE", "TERMINAL", "UNCERTAIN")
ERROR_CODES = (
    "TRANSIENT",
    "PERMANENT",
    "TIMEOUT_UNKNOWN",
    "UNKNOWN_RESULT",
    "LEASE_EXPIRED",
    "EXHAUSTED",
    "LEGACY_FAILED",
    "LEGACY_UNKNOWN",
    "NO_RECIPIENT",
)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("notification_id"),
        UniqueConstraint("idempotency_key"),
        CheckConstraint(
            "channel = 'WHATSAPP_MOCK' AND contract_version = 1",
            name="contract_allowed",
        ),
        CheckConstraint(
            "event_type IN ('TRIP_STARTED','OCCURRENCE_REGISTERED')",
            name="event_type_allowed",
        ),
        CheckConstraint(f"status IN {STATES}", name="status_allowed"),
        CheckConstraint(
            "attempt_count >= 0 AND generation >= attempt_count", name="counters_valid"
        ),
        CheckConstraint(
            "(status = 'PROCESSING' AND lease_expires_at IS NOT NULL) OR (status <> 'PROCESSING' AND lease_expires_at IS NULL)",
            name="lease_matches_status",
        ),
        CheckConstraint(
            f"last_error_code IS NULL OR last_error_code IN {ERROR_CODES}",
            name="error_allowed",
        ),
        Index("ix_outbox_events__status_due", "status", "next_attempt_at", "id"),
        Index("ix_outbox_events__created", "created_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operational_notifications.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="WHATSAPP_MOCK"
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="PENDING"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OutboxAttempt(Base):
    __tablename__ = "outbox_attempts"
    __table_args__ = (
        UniqueConstraint("outbox_event_id", "generation"),
        CheckConstraint("generation >= 0", name="generation_valid"),
        CheckConstraint(
            "result IN ('PROCESSING','SUCCEEDED','RETRYABLE','TERMINAL','UNCERTAIN')",
            name="result_allowed",
        ),
        CheckConstraint(
            "(result = 'PROCESSING' AND finished_at IS NULL) OR (result <> 'PROCESSING' AND finished_at IS NOT NULL)",
            name="finished_matches_result",
        ),
        CheckConstraint(
            f"error_code IS NULL OR error_code IN {ERROR_CODES}", name="error_allowed"
        ),
        CheckConstraint("origin IN ('LEGACY','WORKER')", name="origin_allowed"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    outbox_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="RESTRICT"), nullable=False
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default="WORKER"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(32))


class OutboxRetryCommand(Base):
    __tablename__ = "outbox_retry_commands"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    outbox_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outbox_events.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
