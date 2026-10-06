import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ExternalCommand(Base):
    __tablename__ = "external_commands"
    __table_args__ = (
        UniqueConstraint("integration_id", "event_hash"),
        CheckConstraint("event_hash ~ '^[0-9a-f]{64}$'", name="event_hash_valid"),
        CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name="fingerprint_valid"),
        CheckConstraint(
            "command IN ('START_TRIP', 'START_DELIVERY', 'FINISH_DELIVERY')",
            name="command_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    integration_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    command: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
