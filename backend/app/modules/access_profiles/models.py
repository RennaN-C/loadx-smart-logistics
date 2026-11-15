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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID


class AccessProfile(Base):
    __tablename__ = "access_profiles"
    __table_args__ = (
        CheckConstraint("version > 0", name="positive_version"),
        UniqueConstraint(
            "organization_id", "id", name="uq_access_profiles__organization_id"
        ),
        UniqueConstraint(
            "organization_id",
            "name_key",
            name="uq_access_profiles__organization_name_key",
        ),
        CheckConstraint(
            "name_key = lower(trim(name)) AND length(name_key) > 0",
            name="normalized_name",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        default=lambda: LEGACY_ORGANIZATION_ID,
        server_default=text("'00000000-0000-4000-8000-000000000301'"),
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_key: Mapped[str] = mapped_column(String(120), nullable=False)
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
            ["organization_id", "profile_id"],
            ["access_profiles.organization_id", "access_profiles.id"],
            name="fk_access_profile_permissions__organization_profile",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["permission_code", "delegable"],
            ["access_permissions.code", "access_permissions.delegable"],
            ondelete="RESTRICT",
        ),
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        default=lambda: LEGACY_ORGANIZATION_ID,
        server_default=text("'00000000-0000-4000-8000-000000000301'"),
    )
    permission_code: Mapped[str] = mapped_column(String(80), primary_key=True)
    delegable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
