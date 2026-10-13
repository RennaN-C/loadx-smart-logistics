import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

USERS_FK = "users.id"


class AuthLoginThrottle(Base):
    __tablename__ = "auth_login_throttles"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('ACCOUNT', 'IP')",
            name="scope_allowed",
        ),
        CheckConstraint(
            "failed_count >= 0",
            name="failed_count_non_negative",
        ),
        UniqueConstraint(
            "scope",
            "subject_hash",
            name="uq_auth_login_throttles__scope_subject_hash",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    failed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    blocked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "absolute_expires_at > created_at",
            name="absolute_expiration_after_creation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(USERS_FK, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    idle_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    absolute_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AuthPasswordReset(Base):
    __tablename__ = "auth_password_resets"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="expiration_after_creation"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(USERS_FK, ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthFactor(Base):
    __tablename__ = "auth_factors"
    __table_args__ = (
        CheckConstraint("security_version >= 0", name="version_non_negative"),
        CheckConstraint("last_totp_step >= -1", name="step_valid"),
        CheckConstraint(
            "NOT enabled OR encrypted_secret IS NOT NULL",
            name="enabled_requires_secret",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(USERS_FK, ondelete="CASCADE"), unique=True
    )
    encrypted_secret: Mapped[str | None] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    last_totp_step: Mapped[int] = mapped_column(
        BigInteger, default=-1, server_default="-1"
    )
    security_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="expiration_after_creation"),
        CheckConstraint("purpose IN ('LOGIN', 'ENROLL')", name="purpose_allowed"),
        CheckConstraint("failed_count BETWEEN 0 AND 5", name="attempts_valid"),
        CheckConstraint("security_version >= 0", name="version_non_negative"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(USERS_FK, ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[str] = mapped_column(String(16))
    password_fingerprint: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(32))
    security_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AuthRecoveryCode(Base):
    __tablename__ = "auth_recovery_codes"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(USERS_FK, ondelete="CASCADE"), index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
