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


class OperationalAttachment(Base):
    __tablename__ = "operational_attachments"
    __table_args__ = (
        UniqueConstraint("recorded_by", "event_id"),
        *(
            Index(
                f"ix_operational_attachments__{resource}_recorded",
                f"{resource}_id",
                "recorded_at",
                "id",
            )
            for resource in ("order", "trip", "delivery", "occurrence")
        ),
        CheckConstraint(
            "num_nonnulls(order_id, trip_id, delivery_id, occurrence_id) = 1",
            name="exactly_one_resource",
        ),
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
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT")
    )
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT")
    )
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("deliveries.id", ondelete="RESTRICT")
    )
    occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("occurrences.id", ondelete="RESTRICT")
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_operational_attachments__recorded_by_users",
        ),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
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
            name="fk_operational_attachments__revoked_by_users",
        )
    )

    @property
    def resource_type(self) -> str:
        return next(
            resource
            for resource, column in RESOURCE_COLUMNS.items()
            if getattr(self, column) is not None
        )

    @property
    def resource_id(self) -> uuid.UUID:
        return getattr(self, RESOURCE_COLUMNS[self.resource_type])


RESOURCE_COLUMNS = {
    "orders": "order_id",
    "trips": "trip_id",
    "deliveries": "delivery_id",
    "occurrences": "occurrence_id",
}
