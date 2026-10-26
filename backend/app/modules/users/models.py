import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER', 'CUSTOM')",
            name="role_allowed",
        ),
        CheckConstraint(
            "(role = 'CUSTOM') = (custom_profile_id IS NOT NULL)",
            name="custom_profile_role",
        ),
    )

    custom_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("access_profiles.id", ondelete="RESTRICT"), index=True
    )

    @property
    def permissions(self) -> list[str]:
        from app.modules.access_profiles.catalog import permissions_for

        return sorted(permissions_for(self))

    @property
    def custom_profile_name(self) -> str | None:
        return getattr(self, "_custom_profile_name", None)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("drivers.id", ondelete="RESTRICT"), unique=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
