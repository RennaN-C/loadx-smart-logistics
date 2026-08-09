import base64
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.modules.auth.models import AuthSession
from app.modules.auth.sessions import (
    AuthSessionInactiveUserError,
    AuthSessionInvalidError,
    AuthSessionService,
)
from app.modules.users.models import User

SQLITE_TABLES = (User.__table__, AuthSession.__table__)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)

    def advance(self, delta: timedelta) -> None:
        self.now += delta


def create_user(db_session: Session, *, active: bool = True) -> User:
    user = User(
        name="Usuário de Sessão",
        email="session-user@example.test",
        password_hash="not-used-by-session-tests",
        role="ADMIN",
        active=active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_service(db_session: Session, clock: Clock) -> AuthSessionService:
    return AuthSessionService(
        db_session,
        secret_key="test-secret-key-with-at-least-32-characters",
        now_provider=lambda: clock.now,
    )


def decode_token_bytes(token: str) -> bytes:
    padding = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(token + padding)


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def test_create_session_persists_only_hash_of_256_bit_token(
    db_session: Session,
) -> None:
    clock = Clock()
    user = create_user(db_session)
    service = make_service(db_session, clock)

    issued = service.create_session(user.id)

    assert len(decode_token_bytes(issued.token)) == 32
    assert issued.auth_session.token_hash == service.hash_token(issued.token)
    assert issued.auth_session.token_hash != issued.token
    assert issued.token not in repr(issued.auth_session.__dict__)
    assert as_utc(issued.auth_session.idle_expires_at) == clock.now + timedelta(
        minutes=30
    )
    assert as_utc(issued.auth_session.absolute_expires_at) == clock.now + timedelta(
        hours=8
    )


def test_resolve_session_slides_idle_expiration_without_exceeding_absolute(
    db_session: Session,
) -> None:
    clock = Clock()
    user = create_user(db_session)
    service = make_service(db_session, clock)
    issued = service.create_session(user.id)

    for _ in range(23):
        clock.advance(timedelta(minutes=20))
        service.resolve_session(issued.token)
    clock.advance(timedelta(minutes=10))
    resolved = service.resolve_session(issued.token)

    assert resolved.user.id == user.id
    assert as_utc(resolved.auth_session.last_seen_at) == clock.now
    assert as_utc(resolved.auth_session.idle_expires_at) == as_utc(
        issued.auth_session.absolute_expires_at
    )


@pytest.mark.parametrize(
    "elapsed",
    [timedelta(minutes=30), timedelta(hours=8)],
)
def test_resolve_session_rejects_idle_or_absolute_expiration(
    db_session: Session,
    elapsed: timedelta,
) -> None:
    clock = Clock()
    user = create_user(db_session)
    service = make_service(db_session, clock)
    issued = service.create_session(user.id)
    clock.advance(elapsed)

    with pytest.raises(AuthSessionInvalidError):
        service.resolve_session(issued.token)

    db_session.refresh(issued.auth_session)
    assert as_utc(issued.auth_session.revoked_at) == clock.now


def test_revoke_session_and_all_user_sessions_are_immediate(
    db_session: Session,
) -> None:
    clock = Clock()
    user = create_user(db_session)
    service = make_service(db_session, clock)
    first = service.create_session(user.id)
    second = service.create_session(user.id)

    service.revoke_session(first.token)
    assert service.revoke_all_for_user(user.id) == 1

    with pytest.raises(AuthSessionInvalidError):
        service.resolve_session(first.token)
    with pytest.raises(AuthSessionInvalidError):
        service.resolve_session(second.token)


def test_resolve_session_revokes_inactive_user_sessions(db_session: Session) -> None:
    clock = Clock()
    user = create_user(db_session)
    service = make_service(db_session, clock)
    issued = service.create_session(user.id)
    user.active = False
    db_session.add(user)
    db_session.commit()

    with pytest.raises(AuthSessionInactiveUserError):
        service.resolve_session(issued.token)

    db_session.refresh(issued.auth_session)
    assert as_utc(issued.auth_session.revoked_at) == clock.now


def test_resolve_session_uses_current_database_role(db_session: Session) -> None:
    clock = Clock()
    user = create_user(db_session)
    service = make_service(db_session, clock)
    issued = service.create_session(user.id)
    user.role = "CHECKER"
    db_session.add(user)
    db_session.commit()

    resolved = service.resolve_session(issued.token)

    assert resolved.user.role == "CHECKER"


def test_csrf_token_is_stable_tied_to_session_and_constant_time_validated(
    db_session: Session,
) -> None:
    clock = Clock()
    user = create_user(db_session)
    service = make_service(db_session, clock)
    first = service.create_session(user.id)
    second = service.create_session(user.id)

    assert service.csrf_token_for(first.token) == first.csrf_token
    assert service.validate_csrf_token(first.token, first.csrf_token) is True
    assert service.validate_csrf_token(first.token, second.csrf_token) is False
