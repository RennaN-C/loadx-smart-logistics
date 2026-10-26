import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.security import hash_password
from app.core.security_events import SecurityEvent, emit_security_event
from app.modules.auth.identity_repository import IdentityRepository
from app.modules.auth.identity_service import digest
from app.modules.auth.models import AuthPasswordReset
from app.modules.auth.sessions import AuthSessionService
from app.modules.auth.throttling import LoginThrottleService
from app.modules.status_history.schemas import AuditEventCreate
from app.modules.status_history.service import AuditService
from app.modules.users.password_policy import validate_password_policy
from app.modules.users.service import UserService

REQUEST_SCOPE = "recovery-request:"
CONFIRM_SCOPE = "recovery-confirm:"


class PasswordRecoveryService:
    def __init__(
        self, db: Session, *, now_provider: Callable[[], datetime] | None = None
    ) -> None:
        self.db = db
        self.now = now_provider or (lambda: datetime.now(UTC))
        self.repo = IdentityRepository(db)
        self.users = UserService(db)
        self.throttle = LoginThrottleService(db, now_provider=self.now)
        self.sessions = AuthSessionService(db, now_provider=self.now)

    def request(self, email: str, client_ip: str) -> tuple[str, str] | None:
        self.throttle.ensure_login_allowed(
            REQUEST_SCOPE + email, REQUEST_SCOPE + client_ip
        )
        self.throttle.record_failed_login(
            REQUEST_SCOPE + email, REQUEST_SCOPE + client_ip
        )
        # Equal cryptographic work regardless of account existence.
        token = secrets.token_urlsafe(32)
        token_hash = digest(token)
        user = self.users.get_user_by_email(email)
        result = None
        if user is not None:
            user = self.users.lock_account(user.id)
            if user.active:
                now = self.now()
                self.repo.invalidate_resets(user.id, now)
                self.repo.add(
                    AuthPasswordReset(
                        user_id=user.id,
                        token_hash=token_hash,
                        created_at=now,
                        expires_at=now + timedelta(minutes=15),
                    )
                )
                result = (user.email, token)
        self.db.commit()
        emit_security_event(SecurityEvent.RECOVERY_REQUESTED)
        return result

    def confirm(self, token: str, new_password: str, client_ip: str) -> None:
        validated_password = validate_password_policy(new_password)
        self.throttle.ensure_login_allowed(
            CONFIRM_SCOPE + digest(token), CONFIRM_SCOPE + client_ip
        )
        # Account-independent expensive work avoids validity-dependent hash timing.
        password_hash = hash_password(validated_password)
        user_id = self.repo.reset_user(digest(token))
        if user_id is None:
            self._reject(token, client_ip)
        self.throttle.ensure_login_allowed(
            "recovery-account:" + str(user_id), CONFIRM_SCOPE + client_ip
        )
        user = self.users.lock_account(user_id)
        reset = self.repo.reset(digest(token))
        if (
            reset is None
            or reset.consumed_at is not None
            or self.sessions._as_utc(reset.expires_at) <= self.now()
            or not user.active
        ):
            self.db.rollback()
            self.throttle.record_failed_login(
                "recovery-account:" + str(user_id), CONFIRM_SCOPE + client_ip
            )
            self._reject(token, client_ip)
        user.password_hash = password_hash
        reset.consumed_at = self.now()
        self.repo.invalidate_resets(user.id, self.now())
        self.sessions.stage_revoke_all_for_user(user.id)
        AuditService(self.db).stage_administrative_event(
            AuditEventCreate(
                event_type="USER_UPDATED",
                entity_type="USER",
                entity_id=user.id,
                actor_id=user.id,
                changed_fields=["password"],
            )
        )
        self.db.commit()
        emit_security_event(SecurityEvent.RECOVERY_CONSUMED, user_id=str(user.id))
        emit_security_event(SecurityEvent.USER_SESSIONS_REVOKED, user_id=str(user.id))

    def _reject(self, token: str, client_ip: str) -> None:
        self.throttle.record_failed_login(
            CONFIRM_SCOPE + digest(token), CONFIRM_SCOPE + client_ip
        )
        emit_security_event(SecurityEvent.RECOVERY_REJECTED)
        raise ApiError(
            400,
            "AUTH_RECOVERY_INVALID",
            "Link inválido ou expirado. Solicite uma nova recuperação.",
        )
