import hashlib
import hmac
import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.auth.models import AuthLoginThrottle
from app.modules.auth.repository import AuthLoginThrottleRepository

LOGIN_THROTTLE_SCOPES = ("ACCOUNT", "IP")
LOGIN_FAILURE_DELAYS_SECONDS = (60, 300, 900, 3_600)
LOGIN_FAILURES_BEFORE_DELAY = 4


class AuthRateLimitedError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Authentication is temporarily rate limited")
        self.retry_after_seconds = retry_after_seconds


class LoginThrottleService:
    def __init__(
        self,
        db: Session,
        *,
        secret_key: str = settings.secret_key,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.db = db
        self.repository = AuthLoginThrottleRepository(db)
        self.secret_key = secret_key.encode("utf-8")
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def ensure_login_allowed(self, email: str, client_ip: str) -> None:
        now = self.now_provider()
        retry_after_seconds = 0
        for scope, subject_hash in self._subject_hashes(email, client_ip):
            throttle = self.repository.get_for_update(scope, subject_hash)
            if throttle is None or throttle.blocked_until is None:
                continue
            blocked_until = throttle.blocked_until
            if blocked_until.tzinfo is None:
                blocked_until = blocked_until.replace(tzinfo=UTC)
            remaining_seconds = math.ceil((blocked_until - now).total_seconds())
            retry_after_seconds = max(retry_after_seconds, remaining_seconds)

        if retry_after_seconds > 0:
            raise AuthRateLimitedError(retry_after_seconds)

    def record_failed_login(self, email: str, client_ip: str) -> int:
        try:
            return self._record_failed_login(email, client_ip)
        except IntegrityError:
            self.db.rollback()
            return self._record_failed_login(email, client_ip)

    def reset_after_success(self, email: str, client_ip: str) -> None:
        for scope, subject_hash in self._subject_hashes(email, client_ip):
            throttle = self.repository.get_for_update(scope, subject_hash)
            if throttle is not None:
                self.repository.delete(throttle)
        self.db.commit()

    def hash_subject(self, scope: str, subject: str) -> str:
        message = f"{scope}:{subject}".encode()
        return hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()

    def _record_failed_login(self, email: str, client_ip: str) -> int:
        now = self.now_provider()
        longest_delay = 0
        for scope, subject_hash in self._subject_hashes(email, client_ip):
            throttle = self.repository.get_for_update(scope, subject_hash)
            if throttle is None:
                throttle = self.repository.add(
                    AuthLoginThrottle(
                        scope=scope,
                        subject_hash=subject_hash,
                        failed_count=0,
                    )
                )

            throttle.failed_count += 1
            delay_seconds = self._delay_for_failure_count(throttle.failed_count)
            throttle.blocked_until = (
                now + timedelta(seconds=delay_seconds) if delay_seconds else None
            )
            longest_delay = max(longest_delay, delay_seconds)
        self.db.commit()
        return longest_delay

    def _subject_hashes(
        self,
        email: str,
        client_ip: str,
    ) -> tuple[tuple[str, str], tuple[str, str]]:
        return (
            ("ACCOUNT", self.hash_subject("ACCOUNT", email)),
            ("IP", self.hash_subject("IP", client_ip)),
        )

    @staticmethod
    def _delay_for_failure_count(failed_count: int) -> int:
        delay_index = failed_count - LOGIN_FAILURES_BEFORE_DELAY - 1
        if delay_index < 0:
            return 0
        return LOGIN_FAILURE_DELAYS_SECONDS[
            min(delay_index, len(LOGIN_FAILURE_DELAYS_SECONDS) - 1)
        ]
