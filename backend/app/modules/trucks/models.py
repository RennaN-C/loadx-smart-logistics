import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Truck(Base):
    __tablename__ = "trucks"
    __table_args__ = (
        CheckConstraint(
            "internal_width_cm > 0 AND internal_height_cm > 0 AND internal_length_cm > 0",
            name="dimensions_positive",
        ),
        CheckConstraint("max_weight_kg > 0", name="max_weight_positive"),
        CheckConstraint(
            "odometer_km IS NULL OR odometer_km >= 0", name="odometer_nonnegative"
        ),
        CheckConstraint(
            "next_service_km IS NULL OR next_service_km >= 0",
            name="next_service_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    plate: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    internal_width_cm: Mapped[int] = mapped_column(nullable=False)
    internal_height_cm: Mapped[int] = mapped_column(nullable=False)
    internal_length_cm: Mapped[int] = mapped_column(nullable=False)
    max_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    odometer_km: Mapped[int | None] = mapped_column(BigInteger)
    next_service_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_service_km: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TruckMaintenance(Base):
    __tablename__ = "truck_maintenances"
    __table_args__ = (
        CheckConstraint("kind IN ('PREVENTIVE', 'CORRECTIVE')", name="kind_allowed"),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="period_valid"),
        CheckConstraint("cost IS NULL OR cost >= 0", name="cost_nonnegative"),
        CheckConstraint(
            "odometer_km IS NULL OR odometer_km >= 0", name="odometer_nonnegative"
        ),
        CheckConstraint(
            "completion_odometer_km IS NULL OR completion_odometer_km >= 0",
            name="completion_odometer_nonnegative",
        ),
        CheckConstraint(
            "next_service_km IS NULL OR next_service_km >= 0",
            name="next_service_nonnegative",
        ),
        Index("ix_truck_maintenances__truck_period", "truck_id", "starts_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    truck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trucks.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    workshop: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(String(2000))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    odometer_km: Mapped[int | None] = mapped_column(BigInteger)
    completion_odometer_km: Mapped[int | None] = mapped_column(BigInteger)
    next_service_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_service_km: Mapped[int | None] = mapped_column(BigInteger)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
