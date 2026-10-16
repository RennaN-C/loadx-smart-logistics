import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AccessProfile(Base):
    __tablename__ = "access_profiles"
    __table_args__ = (
        CheckConstraint("version > 0", name="positive_version"),
        CheckConstraint(
            "name_key = lower(btrim(name)) AND length(name_key) > 0",
            name="normalized_name",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PermissionReference(Base):
    __tablename__ = "access_permissions"
    __table_args__ = (UniqueConstraint("code", "delegable"),)
    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    delegable: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ProfilePermission(Base):
    __tablename__ = "access_profile_permissions"
    __table_args__ = (
        CheckConstraint("delegable = true", name="delegable_only"),
        ForeignKeyConstraint(
            ["permission_code", "delegable"],
            ["access_permissions.code", "access_permissions.delegable"],
            ondelete="RESTRICT",
        ),
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("access_profiles.id", ondelete="RESTRICT"), primary_key=True
    )
    permission_code: Mapped[str] = mapped_column(String(80), primary_key=True)
    delegable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
