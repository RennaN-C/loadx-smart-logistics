"""A trusted device waives only the login factor, never password or reauthentication."""

import hashlib
import hmac
import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security_events import SecurityEvent, emit_security_event
from app.modules.auth.identity_repository import IdentityRepository
from app.modules.auth.models import AuthFactor, AuthTrustedDevice
from app.modules.auth.schemas import TrustedDeviceListRead, TrustedDeviceRead
from app.modules.auth.totp import IdentityUnavailableError
from app.modules.auth.trusted_device_repository import TrustedDeviceRepository
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.users.models import User

if TYPE_CHECKING:
    from app.modules.auth.sessions import ResolvedAuthSession

MAX_LIVE_DEVICES = 20


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def security_binding(user: User, factor: AuthFactor) -> str:
    # The challenge security_version also changes on ordinary login; it is not
    # a durable account version. Bind credentials/factor and revoke on security
    # mutations instead, including CUSTOM permission changes and reversals.
    return token_digest(
        json.dumps(
            [
                user.password_hash,
                user.role,
                str(user.custom_profile_id),
                factor.encrypted_secret,
                factor.enabled,
            ]
        )
    )


def stage_audit(
    db: Session, user_id: uuid.UUID, field: str, actor_id: uuid.UUID
) -> None:
    AuditService(db).stage_administrative_event(
        AuditEventCreate(
            event_type="USER_UPDATED",
            entity_type="USER",
            entity_id=user_id,
            actor_id=actor_id,
            changed_fields=[field],
        )
    )


@dataclass(frozen=True)
class IssuedTrustedDevice:
    token: str
    device: AuthTrustedDevice


class TrustedDeviceService:
    def __init__(
        self, db: Session, *, now_provider: Callable[[], datetime] | None = None
    ) -> None:
        self.db = db
        self.repo = TrustedDeviceRepository(db)
        self.now = now_provider or (lambda: datetime.now(UTC))

    def stage_issue(
        self, user: User, factor: AuthFactor, previous_token: str | None
    ) -> IssuedTrustedDevice:
        now = self.now()
        previous = (
            self.repo.find(user.id, token_digest(previous_token))
            if previous_token
            else None
        )
        if previous is not None and previous.revoked_at is None:
            previous.revoked_at = now
            self.db.flush()
        live = self.repo.list_live(user.id, now)
        # Serialised by account lock; bounded list/credential footprint.
        for old in live[: max(0, len(live) - MAX_LIVE_DEVICES + 1)]:
            old.revoked_at = now
        token = secrets.token_urlsafe(32)
        device = self.repo.add(
            AuthTrustedDevice(
                user_id=user.id,
                token_hash=token_digest(token),
                security_binding=security_binding(user, factor),
                created_at=now,
                last_used_at=now,
                expires_at=now + timedelta(days=settings.trusted_device_days),
            )
        )
        stage_audit(self.db, user.id, "trusted_device_created", user.id)
        return IssuedTrustedDevice(token, device)

    def stage_authorize(
        self, user: User, factor: AuthFactor | None, token: str | None
    ) -> AuthTrustedDevice | None:
        if (
            not settings.trusted_devices_enabled
            or not token
            or len(token) > 128
            or not factor
            or not factor.enabled
        ):
            return None
        try:
            device = self.repo.find(user.id, token_digest(token))
            now = self.now()
            if (
                device is None
                or device.revoked_at is not None
                or device.created_at > now
                or device.expires_at <= now
                or not hmac.compare_digest(
                    device.security_binding, security_binding(user, factor)
                )
            ):
                return None
            device.last_used_at = now
            stage_audit(self.db, user.id, "trusted_device_used", user.id)
            return device
        except SQLAlchemyError:
            self.db.rollback()
            raise IdentityUnavailableError from None

    def list_own(
        self, current: "ResolvedAuthSession", token: str | None
    ) -> TrustedDeviceListRead:
        # Lock account/session to serialize listing with security mutations, too.
        from app.modules.auth.account_service import AccountService

        user = AccountService(self.db, now_provider=self.now)._lock_account(current)
        factor = IdentityRepository(self.db).find_factor(user.id)
        binding = security_binding(user, factor) if factor else ""
        items = [
            TrustedDeviceRead(
                id=d.id,
                created_at=d.created_at,
                last_used_at=d.last_used_at,
                expires_at=d.expires_at,
                current=bool(
                    token and hmac.compare_digest(d.token_hash, token_digest(token))
                ),
            )
            for d in self.repo.list_live(user.id, self.now())
            if hmac.compare_digest(d.security_binding, binding)
        ]
        self.db.commit()
        return TrustedDeviceListRead(
            enabled=settings.trusted_devices_enabled,
            lifetime_days=settings.trusted_device_days,
            items=items,
        )

    def revoke_own(
        self,
        current: "ResolvedAuthSession",
        *,
        device_id: uuid.UUID | None = None,
        current_token: str | None = None,
        all_devices: bool = False,
    ) -> bool:
        from app.modules.auth.account_service import AccountService

        user = AccountService(self.db, now_provider=self.now)._lock_account(current)
        if not all_devices and device_id is None:
            device = (
                self.repo.find(user.id, token_digest(current_token))
                if current_token
                else None
            )
            if device is None:
                self.db.commit()
                return True
            device_id = device.id
        own_cookie = (
            self.repo.find(user.id, token_digest(current_token))
            if current_token
            else None
        )
        clear_cookie = all_devices or bool(own_cookie and own_cookie.id == device_id)
        count = self.repo.revoke(user.id, self.now(), device_id)
        if count:
            stage_audit(self.db, user.id, "trusted_devices_revoked", user.id)
        self.db.commit()
        emit_security_event(
            SecurityEvent.TRUSTED_DEVICES_REVOKED,
            user_id=str(user.id),
            revoked_count=count,
        )
        return clear_cookie
