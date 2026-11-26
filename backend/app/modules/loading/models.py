import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LoadingSession(Base):
    __tablename__ = "loading_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "load_plan_id"],
            ["load_plans.organization_id", "load_plans.id"],
            name="fk_loading_sessions__organization_plan",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id",
            "id",
            "load_plan_id",
            name="uq_loading_sessions__org_id_plan",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'FINISHED')",
            name="status_allowed",
        ),
        CheckConstraint(
            "(status = 'PENDING' AND started_at IS NULL AND finished_at IS NULL) "
            "OR (status = 'IN_PROGRESS' AND started_at IS NOT NULL AND finished_at IS NULL) "
            "OR (status = 'FINISHED' AND started_at IS NOT NULL AND finished_at IS NOT NULL AND finished_at >= started_at)",
            name="timestamps_consistent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    load_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("load_plans.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items: Mapped[list["LoadingSessionItem"]] = relationship(
        back_populates="session",
        order_by="LoadingSessionItem.id",
        foreign_keys="LoadingSessionItem.loading_session_id",
    )


class LoadingSessionItem(Base):
    __tablename__ = "loading_session_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "loading_session_id", "load_plan_id"],
            [
                "loading_sessions.organization_id",
                "loading_sessions.id",
                "loading_sessions.load_plan_id",
            ],
            name="fk_loading_session_items__org_session_plan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "load_plan_id", "load_plan_item_id"],
            [
                "load_plan_items.organization_id",
                "load_plan_items.load_plan_id",
                "load_plan_items.id",
            ],
            name="fk_loading_session_items__org_plan_item",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "loading_session_id",
            "load_plan_item_id",
            name="uq_loading_session_items__session_plan_item",
        ),
        CheckConstraint("status IN ('PENDING', 'CHECKED')", name="status_allowed"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    load_plan_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    loading_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("loading_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    load_plan_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("load_plan_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", server_default="PENDING"
    )
    session: Mapped[LoadingSession] = relationship(
        back_populates="items", foreign_keys=[loading_session_id]
    )
