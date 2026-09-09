from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.modules.auth.models import AuthLoginThrottle
from app.modules.auth.throttling import AuthRateLimitedError, LoginThrottleService

SQLITE_TABLES = (AuthLoginThrottle.__table__,)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


def make_service(db_session: Session, clock: Clock) -> LoginThrottleService:
    return LoginThrottleService(
        db_session,
        secret_key="test-secret-key-with-at-least-32-characters",
        now_provider=lambda: clock.now,
    )


def test_fifth_failure_starts_progressive_delays(db_session: Session) -> None:
    clock = Clock()
    service = make_service(db_session, clock)
    expected_delays = (60, 300, 900, 3_600, 3_600)

    for _ in range(4):
        assert service.record_failed_login("admin@example.test", "192.0.2.10") == 0

    for expected_delay in expected_delays:
        assert (
            service.record_failed_login("admin@example.test", "192.0.2.10")
            == expected_delay
        )
        with pytest.raises(AuthRateLimitedError) as error_info:
            service.ensure_login_allowed("admin@example.test", "192.0.2.10")
        assert error_info.value.retry_after_seconds == expected_delay
        clock.advance(expected_delay + 1)


def test_throttle_applies_independently_to_account_and_ip(db_session: Session) -> None:
    clock = Clock()
    service = make_service(db_session, clock)
    for index in range(5):
        service.record_failed_login("admin@example.test", f"192.0.2.{index}")

    with pytest.raises(AuthRateLimitedError):
        service.ensure_login_allowed("admin@example.test", "198.51.100.1")

    for index in range(5):
        service.record_failed_login(f"user-{index}@example.test", "203.0.113.10")

    with pytest.raises(AuthRateLimitedError):
        service.ensure_login_allowed("new-user@example.test", "203.0.113.10")


def test_success_resets_account_and_ip_counters(db_session: Session) -> None:
    clock = Clock()
    service = make_service(db_session, clock)
    for _ in range(5):
        service.record_failed_login("admin@example.test", "192.0.2.10")

    service.reset_after_success("admin@example.test", "192.0.2.10")

    service.ensure_login_allowed("admin@example.test", "192.0.2.10")
    assert db_session.query(AuthLoginThrottle).count() == 0


def test_subject_hash_does_not_persist_raw_identifier(db_session: Session) -> None:
    clock = Clock()
    service = make_service(db_session, clock)

    service.record_failed_login("admin@example.test", "192.0.2.10")
    stored_hashes = {
        throttle.subject_hash for throttle in db_session.query(AuthLoginThrottle).all()
    }

    assert len(stored_hashes) == 2
    assert "admin@example.test" not in stored_hashes
    assert "192.0.2.10" not in stored_hashes
    assert all(len(value) == 64 for value in stored_hashes)
