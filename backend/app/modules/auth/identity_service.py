"""Local second-factor orchestration; no logistic-domain dependencies."""

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError
from app.core.security import verify_password
from app.core.security_events import SecurityEvent, emit_security_event
from app.modules.auth.account_service import AccountService
from app.modules.auth.identity_repository import IdentityRepository
from app.modules.auth.models import AuthChallenge, AuthFactor
from app.modules.auth.schemas import MFA_REQUIRED_ROLES
from app.modules.auth.sessions import (
    AuthSessionService,
    IssuedAuthSession,
    ResolvedAuthSession,
)
from app.modules.auth.throttling import LoginThrottleService
from app.modules.auth.totp import (
    cipher,
    decrypt_secret,
    encrypt_secret,
    matching_step,
    new_secret,
    provisioning_uri,
)
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.users.models import User
from app.modules.users.service import UserService

MANAGE_SCOPE = "mfa-manage:"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class MfaChallengeResult:
    challenge_token: str
    purpose: str
    expires_at: datetime


@dataclass(frozen=True)
class MfaCompletion:
    user: User
    session: IssuedAuthSession
    recovery_codes: list[str]


class IdentityService:
    def __init__(
        self,
        db: Session,
        *,
        key: str | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.db = db
        configured_key = settings.mfa_encryption_key
        default_key = configured_key.get_secret_value() if configured_key else None
        self.key = key if key is not None else default_key
        self.now = now_provider or (lambda: datetime.now(UTC))
        self.recovery_used: str | None = None
        self.repo = IdentityRepository(db)
        self.users = UserService(db)
        self.sessions = AuthSessionService(db, now_provider=self.now)
        self.throttle = LoginThrottleService(db, now_provider=self.now)

    def required(self, user: User) -> bool:
        factor = self.repo.find_factor(user.id)
        return user.role in MFA_REQUIRED_ROLES or bool(factor and factor.enabled)

    def begin(self, user: User, *, expected_hash: str) -> MfaChallengeResult:
        cipher(self.key)
        user = self.users.lock_account(user.id)
        if not user.active or user.password_hash != expected_hash:
            raise ApiError(
                401, "AUTH_INVALID_CREDENTIALS", "E-mail ou senha inválidos."
            )
        factor = self.repo.factor(user.id)
        now = self.now()
        token = secrets.token_urlsafe(32)
        # One outstanding challenge per account prevents stale enrollment races.
        self.repo.invalidate_challenges(user.id, now)
        self.db.refresh(factor)
        purpose = "LOGIN" if factor.enabled else "ENROLL"
        self.repo.add(
            AuthChallenge(
                user_id=user.id,
                token_hash=digest(token),
                purpose=purpose,
                password_fingerprint=digest(user.password_hash),
                role=user.role,
                security_version=factor.security_version,
                created_at=now,
                expires_at=now + timedelta(minutes=5),
            )
        )
        self.db.commit()
        return MfaChallengeResult(token, purpose, now + timedelta(minutes=5))

    def _challenge(
        self, token: str, client_ip: str
    ) -> tuple[User, AuthFactor, AuthChallenge]:
        # Invalid random credentials cannot bypass the per-origin counter.
        self.throttle.ensure_login_allowed("mfa:" + digest(token), "mfa:" + client_ip)
        user_id = self.repo.challenge_user(digest(token))
        if user_id is None:
            self.throttle.record_failed_login(
                "mfa:" + digest(token), "mfa:" + client_ip
            )
            self._invalid()
        user = self.users.lock_account(user_id)
        factor = self.repo.factor(user.id)
        challenge = self.repo.challenge(digest(token))
        if (
            challenge is None
            or challenge.consumed_at is not None
            or self.sessions._as_utc(challenge.expires_at) <= self.now()
            or challenge.failed_count >= 5
            or not user.active
            or challenge.role != user.role
            or challenge.password_fingerprint != digest(user.password_hash)
            or challenge.security_version != factor.security_version
        ):
            self._invalid()
        return user, factor, challenge

    def setup(self, token: str, client_ip: str) -> str:
        user, factor, challenge = self._challenge(token, client_ip)
        if challenge.purpose != "ENROLL" or factor.enabled:
            self._invalid()
        # Repeated setup rotates pending secret, never discloses an active secret.
        secret = new_secret()
        factor.encrypted_secret = encrypt_secret(secret, self.key)
        factor.last_totp_step = -1
        self.db.commit()
        return provisioning_uri(secret, user.email)

    def complete(self, token: str, code: str, client_ip: str) -> MfaCompletion:
        user, factor, challenge = self._challenge(token, client_ip)
        # Durable account/origin budget remains across replacement challenges.
        self.throttle.ensure_login_allowed(
            "mfa-account:" + str(user.id), "mfa:" + client_ip
        )
        if not self._verify(
            factor, user, code, allow_recovery=challenge.purpose == "LOGIN"
        ):
            challenge.failed_count += 1
            if challenge.failed_count >= 5:
                challenge.consumed_at = self.now()
            self.db.commit()
            self.throttle.record_failed_login(
                "mfa-account:" + str(user.id), "mfa:" + client_ip
            )
            emit_security_event(
                SecurityEvent.MFA_REJECTED, alert=True, user_id=str(user.id)
            )
            self._invalid()
        codes = []
        if challenge.purpose == "ENROLL":
            # Revoke password sessions created while optional enrollment was pending.
            self.sessions.stage_revoke_all_for_user(user.id)
            factor.enabled = True
            codes = self._codes(user)
            self._audit(user, "mfa_enabled")

        challenge.consumed_at = self.now()
        # create_session commits consumption + factor/recovery + session atomically.
        session = self.sessions.create_session(
            user.id, expected_password_hash=user.password_hash
        )
        # A password-only challenge cannot clear budgets. Clear them only after
        # the full authentication commits, without reversing login's lock order.
        self.throttle.reset_after_success(user.email, client_ip)
        self.throttle.reset_after_success(
            "mfa-account:" + str(user.id), "mfa:" + client_ip
        )
        if codes:
            emit_security_event(SecurityEvent.MFA_CONFIGURED, user_id=str(user.id))
        self.emit_committed_security_events()
        emit_security_event(SecurityEvent.MFA_VALIDATED, user_id=str(user.id))
        return MfaCompletion(user, session, codes)

    def _verify(
        self, factor: AuthFactor, user: User, code: str, *, allow_recovery: bool = True
    ) -> bool:
        self.recovery_used = None
        if factor.encrypted_secret:
            secret = decrypt_secret(factor.encrypted_secret, self.key)
            step = matching_step(
                secret, code, self.now().timestamp(), factor.last_totp_step
            )
            if step is not None:
                factor.last_totp_step = step
                return True
        if allow_recovery and factor.enabled:
            recovery = self.repo.recovery(user.id, digest(code))
            if recovery is not None and recovery.consumed_at is None:
                recovery.consumed_at = self.now()
                self.recovery_used = str(user.id)
                return True
        return False

    def _codes(self, user: User) -> list[str]:
        codes = [secrets.token_hex(16) for _ in range(10)]
        self.repo.replace_codes(user.id, [digest(code) for code in codes])
        return codes

    def status(self, current: ResolvedAuthSession) -> dict[str, bool]:
        factor = self.repo.find_factor(current.user.id)
        return {
            "enabled": bool(factor and factor.enabled),
            "required": current.user.role in MFA_REQUIRED_ROLES,
        }

    def _reauth(
        self, current: ResolvedAuthSession, password: str, code: str, client_ip: str
    ) -> tuple[User, AuthFactor]:
        # Management mutations always use user -> throttles -> factor/session.
        # Profile changes may already hold the user lock; never reverse that order.
        user = AccountService(self.db, now_provider=self.now)._lock_account(current)
        self.throttle.ensure_login_allowed(
            MANAGE_SCOPE + str(current.user.id), MANAGE_SCOPE + client_ip
        )
        factor = self.repo.factor(user.id)
        if not verify_password(password, user.password_hash) or (
            factor.enabled and not self._verify(factor, user, code)
        ):
            self.db.rollback()
            self.throttle.record_failed_login(
                MANAGE_SCOPE + str(user.id), MANAGE_SCOPE + client_ip
            )
            emit_security_event(
                SecurityEvent.MFA_REJECTED, alert=True, user_id=str(user.id)
            )
            self._invalid()
        return user, factor

    def manage(
        self,
        current: ResolvedAuthSession,
        password: str,
        code: str,
        action: str,
        client_ip: str,
    ) -> list[str]:
        user, factor = self._reauth(current, password, code, client_ip)
        if action == "regenerate" and factor.enabled:
            codes = self._codes(user)
            self._audit(user, "mfa_recovery_codes")
            self.db.commit()
            self.emit_committed_security_events()
            emit_security_event(
                SecurityEvent.MFA_CODES_REGENERATED, user_id=str(user.id)
            )
            return codes
        if action == "disable" and factor.enabled:
            factor.enabled = False
            factor.encrypted_secret = None
            factor.last_totp_step = -1
            self.repo.replace_codes(user.id, [])
            self.sessions.stage_revoke_all_for_user(user.id)
            self._audit(user, "mfa_disabled")
            self.db.commit()
            self.emit_committed_security_events()
            emit_security_event(
                SecurityEvent.MFA_DISABLED, alert=True, user_id=str(user.id)
            )
            return []
        self._invalid()

    def enroll_own(
        self, current: ResolvedAuthSession, password: str, client_ip: str
    ) -> MfaChallengeResult:
        cipher(self.key)
        user, factor = self._reauth(current, password, "", client_ip)
        if factor.enabled:
            self._invalid()
        # End prior full access before transitioning to restricted enrollment.
        self.sessions.stage_revoke_all_for_user(user.id)
        self.db.commit()
        return self.begin(user, expected_hash=user.password_hash)

    def confirm_email_change(
        self, current: ResolvedAuthSession, password: str, code: str, client_ip: str
    ) -> None:
        self._reauth(current, password, code, client_ip)
        self.repo.invalidate_resets(current.user.id, self.now())
        # Caller commits factor replay protection and profile change together.

    def emit_committed_security_events(self) -> None:
        """Emit recovery consumption only after its owning transaction commits."""
        if self.recovery_used is not None:
            emit_security_event(
                SecurityEvent.MFA_RECOVERY_USED, alert=True, user_id=self.recovery_used
            )
            self.recovery_used = None

    def _audit(self, user: User, field: str) -> None:
        AuditService(self.db).stage_administrative_event(
            AuditEventCreate(
                event_type="USER_UPDATED",
                entity_type="USER",
                entity_id=user.id,
                actor_id=user.id,
                changed_fields=[field],
            )
        )

    @staticmethod
    def _invalid() -> None:
        raise ApiError(
            400,
            "AUTH_MFA_INVALID",
            "Verificação inválida ou expirada. Tente novamente ou inicie outro login.",
        )
