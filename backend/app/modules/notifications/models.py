import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class OperationalNotification(Base):
    __tablename__ = "operational_notifications"
    __table_args__ = (
        CheckConstraint(
            "(event_type = 'TRIP_STARTED' AND status_history_id IS NOT NULL AND occurrence_id IS NULL) OR "
            "(event_type = 'OCCURRENCE_REGISTERED' AND occurrence_id IS NOT NULL AND status_history_id IS NULL)",
            name="origin_matches_event",
        ),
        CheckConstraint(
            "mock_status IN ('NOT_ATTEMPTED','ATTEMPT_CLAIMED','SIMULATED','FAILED','NO_RECIPIENT')",
            name="mock_status_allowed",
        ),
        CheckConstraint(
            "(mock_status = 'NOT_ATTEMPTED' AND claimed_at IS NULL AND completed_at IS NULL) OR "
            "(mock_status = 'ATTEMPT_CLAIMED' AND claimed_at IS NOT NULL AND completed_at IS NULL) OR "
            "(mock_status IN ('SIMULATED','FAILED','NO_RECIPIENT') AND claimed_at IS NOT NULL AND completed_at IS NOT NULL)",
            name="attempt_timestamps",
        ),
        Index(
            "uq_operational_notifications__history_recipient",
            "event_type",
            "status_history_id",
            "recipient_driver_id",
            unique=True,
            postgresql_where=text("status_history_id IS NOT NULL"),
            sqlite_where=text("status_history_id IS NOT NULL"),
        ),
        Index(
            "uq_operational_notifications__occurrence_recipient",
            "event_type",
            "occurrence_id",
            "recipient_driver_id",
            unique=True,
            postgresql_where=text("occurrence_id IS NOT NULL"),
            sqlite_where=text("occurrence_id IS NOT NULL"),
        ),
        Index(
            "ix_operational_notifications__trip_created", "trip_id", "created_at", "id"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status_history_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("status_history.id", ondelete="RESTRICT")
    )
    occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occurrences.id", ondelete="RESTRICT")
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    mock_status: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="NOT_ATTEMPTED"
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
