import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

TRIP_STATUS_VALUES = ("SCHEDULED", "IN_ROUTE", "FINISHED")
DELIVERY_STATUS_VALUES = ("PENDING", "IN_DELIVERY", "DELIVERED")


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SCHEDULED', 'IN_ROUTE', 'FINISHED')",
            name="status_allowed",
        ),
        CheckConstraint(
            "(status = 'SCHEDULED' AND started_at IS NULL AND finished_at IS NULL) "
            "OR (status = 'IN_ROUTE' AND started_at IS NOT NULL "
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
        UniqueConstraint("order_id", name="uq_deliveries__order_id"),
        CheckConstraint(
            "status IN ('PENDING', 'IN_DELIVERY', 'DELIVERED')",
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
