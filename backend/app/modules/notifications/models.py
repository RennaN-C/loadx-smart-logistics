import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"
    __table_args__ = (
        Index(
            "ix_notification_recipients__user_created",
            "user_id",
            "created_at",
            "notification_id",
        ),
        Index(
            "ix_notification_recipients__unread",
            "user_id",
            postgresql_where=text("read_at IS NULL"),
            sqlite_where=text("read_at IS NULL"),
        ),
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operational_notifications.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        CheckConstraint(
            "category IN ('TRIPS','OCCURRENCES','SECURITY')", name="category_allowed"
        ),
        CheckConstraint(
            "category <> 'SECURITY' OR enabled = true", name="security_required"
        ),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(24), primary_key=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
