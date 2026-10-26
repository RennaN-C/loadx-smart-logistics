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


class DeliveryEvidence(Base):
    __tablename__ = "delivery_evidences"
    __table_args__ = (
        UniqueConstraint("recorded_by", "event_id"),
        Index(
            "ix_delivery_evidences__delivery_recorded",
            "delivery_id",
            "recorded_at",
            "id",
        ),
        CheckConstraint("kind IN ('PHOTO', 'SIGNATURE')", name="kind_allowed"),
        CheckConstraint(
            "media_type IN ('image/png', 'image/jpeg')", name="media_type_allowed"
        ),
        CheckConstraint("size_bytes BETWEEN 1 AND 5242880", name="size_allowed"),
        CheckConstraint(
            "length(sha256) = 64 AND length(fingerprint) = 64", name="hash_lengths"
        ),
        CheckConstraint(
            "(status = 'ACTIVE' AND revoked_at IS NULL AND revoked_by IS NULL) OR "
            "(status = 'REVOKED' AND revoked_at IS NOT NULL AND revoked_by IS NOT NULL)",
            name="revocation_consistent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deliveries.id", ondelete="RESTRICT"), nullable=False
    )
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("status_history.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_delivery_evidences__recorded_by_users",
        ),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_delivery_evidences__revoked_by_users",
        )
    )
