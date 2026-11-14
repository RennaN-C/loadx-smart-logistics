import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

LEGACY_ORGANIZATION_ID = uuid.UUID("00000000-0000-4000-8000-000000000301")

ORGANIZATION_STATUSES = ("PENDING", "ACTIVE", "SUSPENDED", "CANCELED")
MEMBERSHIP_ROLES = (
    "ADMIN",
    "CHECKER",
    "DRIVER",
    "LOGISTICS_MANAGER",
    "CUSTOM",
)
MEMBERSHIP_STATUSES = ("ACTIVE", "SUSPENDED", "REMOVED")


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'ACTIVE', 'SUSPENDED', 'CANCELED')",
            name="status_allowed",
        ),
        CheckConstraint(
            "length(trim(legal_name)) > 0 AND length(trim(display_name)) > 0",
            name="names_not_empty",
        ),
        CheckConstraint("cnpj IS NULL OR length(cnpj) = 14", name="cnpj_length"),
        Index(
            "uq_organizations__cnpj",
            "cnpj",
            unique=True,
            postgresql_where=text("cnpj IS NOT NULL"),
            sqlite_where=text("cnpj IS NOT NULL"),
        ),
        Index(
            "uq_organizations__legacy",
            "is_legacy",
            unique=True,
            postgresql_where=text("is_legacy IS TRUE"),
            sqlite_where=text("is_legacy = 1"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    legal_name: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'")
    )
    is_legacy: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships__organization_user",
        ),
        UniqueConstraint(
            "id",
            "organization_id",
            name="uq_organization_memberships__id_organization",
        ),
        CheckConstraint(
            "role IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER', 'CUSTOM')",
            name="role_allowed",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED', 'REMOVED')",
            name="status_allowed",
        ),
        CheckConstraint(
            "(role = 'CUSTOM') = (custom_profile_id IS NOT NULL)",
            name="custom_profile_role",
        ),
        CheckConstraint(
            "driver_id IS NULL OR role = 'DRIVER'",
            name="driver_role_required",
        ),
        Index(
            "uq_organization_memberships__organization_driver",
            "organization_id",
            "driver_id",
            unique=True,
            postgresql_where=text("driver_id IS NOT NULL"),
            sqlite_where=text("driver_id IS NOT NULL"),
        ),
        Index("ix_organization_memberships__user_status", "user_id", "status"),
        Index(
            "ix_organization_memberships__organization_status_role",
            "organization_id",
            "status",
            "role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("access_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"
    __table_args__ = (
        CheckConstraint(
            "role IN ('ADMIN', 'CHECKER', 'DRIVER', 'LOGISTICS_MANAGER', 'CUSTOM')",
            name="role_allowed",
        ),
        CheckConstraint(
            "(role = 'CUSTOM') = (custom_profile_id IS NOT NULL)",
            name="custom_profile_role",
        ),
        CheckConstraint(
            "length(email_normalized) > 0 AND email_normalized = lower(trim(email_normalized))",
            name="email_normalized",
        ),
        CheckConstraint("length(token_hash) = 64", name="token_hash_length"),
        CheckConstraint("expires_at > created_at", name="expiration_after_creation"),
        CheckConstraint(
            "(accepted_at IS NULL) = (accepted_by_user_id IS NULL)",
            name="accepted_actor_consistent",
        ),
        CheckConstraint(
            "(revoked_at IS NULL) = (revoked_by_user_id IS NULL)",
            name="revoked_actor_consistent",
        ),
        CheckConstraint(
            "accepted_at IS NULL OR revoked_at IS NULL",
            name="terminal_state_exclusive",
        ),
        UniqueConstraint("token_hash", name="uq_organization_invitations__token_hash"),
        Index(
            "uq_organization_invitations__pending_email",
            "organization_id",
            "email_normalized",
            unique=True,
            postgresql_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
            sqlite_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
        ),
        Index(
            "ix_organization_invitations__organization_expiration",
            "organization_id",
            "expires_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("access_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_organization_invitations__invited_by_user",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_organization_invitations__accepted_by_user",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_organization_invitations__revoked_by_user",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformOwnerGrant(Base):
    __tablename__ = "platform_owner_grants"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton"),
        CheckConstraint("length(trim(reason)) > 0", name="reason_not_empty"),
        UniqueConstraint("user_id", name="uq_platform_owner_grants__user"),
    )

    id: Mapped[int] = mapped_column(
        SmallInteger, primary_key=True, default=1, server_default=text("1")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_platform_owner_grants__user",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_platform_owner_grants__granted_by_user",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
