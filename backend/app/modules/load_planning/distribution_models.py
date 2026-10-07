import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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


class LoadDistribution(Base):
    __tablename__ = "load_distributions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROPOSED', 'PARTIALLY_APPROVED', 'APPROVED', 'INCOMPLETE', 'CANCELED')",
            name="status_allowed",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PROPOSED")
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    orders: Mapped[list["LoadDistributionOrder"]] = relationship()
    parts: Mapped[list["LoadDistributionPart"]] = relationship()
    volumes: Mapped[list["LoadDistributionVolume"]] = relationship(
        primaryjoin="LoadDistribution.id == foreign(LoadDistributionVolume.distribution_id)"
    )


class LoadDistributionOrder(Base):
    __tablename__ = "load_distribution_orders"
    __table_args__ = (
        Index(
            "uq_load_distribution_orders__active_order",
            "order_id",
            unique=True,
            postgresql_where=text("active"),
        ),
    )
    distribution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("load_distributions.id", ondelete="RESTRICT"), primary_key=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), primary_key=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LoadDistributionPart(Base):
    __tablename__ = "load_distribution_parts"
    __table_args__ = (
        UniqueConstraint("id", "distribution_id"),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'CANCELED')", name="status_allowed"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    distribution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("load_distributions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    load_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("load_plans.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")


class LoadDistributionVolume(Base):
    __tablename__ = "load_distribution_volumes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["distribution_id", "order_id"],
            [
                "load_distribution_orders.distribution_id",
                "load_distribution_orders.order_id",
            ],
            ondelete="RESTRICT",
            name="fk_load_distribution_volumes__distribution_order",
        ),
        ForeignKeyConstraint(
            ["part_id", "distribution_id"],
            ["load_distribution_parts.id", "load_distribution_parts.distribution_id"],
            ondelete="RESTRICT",
            name="fk_load_distribution_volumes__part",
        ),
        ForeignKeyConstraint(
            ["order_item_id", "order_id", "product_id"],
            ["order_items.id", "order_items.order_id", "order_items.product_id"],
            ondelete="RESTRICT",
            name="fk_load_distribution_volumes__provenance",
        ),
        CheckConstraint(
            "volume_index BETWEEN 1 AND snapshot_quantity", name="identity_range"
        ),
        Index(
            "uq_load_distribution_volumes__active_identity",
            "order_item_id",
            "volume_index",
            unique=True,
            postgresql_where=text("active"),
        ),
        Index("ix_load_distribution_volumes__part_id", "part_id"),
    )
    distribution_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    order_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    volume_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    snapshot_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    part_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
