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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

TRIP_STATUS_VALUES = ("SCHEDULED", "IN_ROUTE", "INTERRUPTED", "FINISHED", "CANCELED")
DELIVERY_STATUS_VALUES = ("PENDING", "IN_DELIVERY", "DELIVERED", "CANCELED")


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SCHEDULED','IN_ROUTE','INTERRUPTED','FINISHED','CANCELED')",
            name="status_allowed",
        ),
        CheckConstraint(
            "(status IN ('SCHEDULED', 'CANCELED') AND started_at IS NULL AND finished_at IS NULL) "
            "OR (status IN ('IN_ROUTE','INTERRUPTED') AND started_at IS NOT NULL "
            "AND finished_at IS NULL) "
            "OR (status = 'FINISHED' AND started_at IS NOT NULL "
            "AND finished_at IS NOT NULL AND finished_at >= started_at)",
            name="timestamps_consistent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    load_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("load_plans.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SCHEDULED",
        server_default="SCHEDULED",
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deliveries: Mapped[list["Delivery"]] = relationship(
        back_populates="trip",
        order_by="Delivery.sequence, Delivery.id",
        passive_deletes="all",
    )


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint("trip_id", "order_id", name="uq_deliveries__trip_order"),
        UniqueConstraint("trip_id", "sequence", name="uq_deliveries__trip_sequence"),
        Index(
            "uq_deliveries__part_order",
            "distribution_part_id",
            "order_id",
            unique=True,
            postgresql_where=text(
                "distribution_part_id IS NOT NULL AND status <> 'CANCELED'"
            ),
            sqlite_where=text(
                "distribution_part_id IS NOT NULL AND status <> 'CANCELED'"
            ),
        ),
        Index(
            "uq_deliveries__legacy_order",
            "order_id",
            unique=True,
            postgresql_where=text(
                "distribution_part_id IS NULL AND status <> 'CANCELED'"
            ),
            sqlite_where=text("distribution_part_id IS NULL AND status <> 'CANCELED'"),
        ),
        CheckConstraint(
            "status IN ('PENDING', 'IN_DELIVERY', 'DELIVERED', 'CANCELED')",
            name="status_allowed",
        ),
        CheckConstraint("sequence > 0", name="sequence_positive"),
        CheckConstraint(
            "(status = 'DELIVERED' AND delivered_at IS NOT NULL) "
            "OR (status <> 'DELIVERED' AND delivered_at IS NULL)",
            name="completion_consistent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    distribution_part_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("load_distribution_parts.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trip: Mapped[Trip] = relationship(back_populates="deliveries")
