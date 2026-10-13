from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import ApiError
from app.modules.auth.identity_service import IdentityService
from app.modules.auth.models import (
    AuthChallenge,
    AuthFactor,
    AuthPasswordReset,
    AuthRecoveryCode,
    AuthSession,
)
from app.modules.auth.recovery_service import PasswordRecoveryService
from app.modules.auth.sessions import AuthSessionService
from app.modules.auth.totp import totp_code
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers

PASSWORD = "senha-local-segura"
NEW_PASSWORD = "outra-frase-segura-local"
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
BASE = "/api/v1/auth"


def account(factory, role="ADMIN"):
    with factory() as db:
        return UserService(db).create_user(
            UserCreate(
                name="Conta fictícia OC98",
                email="oc98@example.test",
                password=PASSWORD,
                role=role,
            )
        )


def enrollment(factory, user):
    db = factory()
    service = IdentityService(db, now_provider=lambda: NOW)
    challenge = service.begin(user, expected_hash=user.password_hash)
    uri = service.setup(challenge.challenge_token, "origin")
    secret = parse_qs(urlsplit(uri).query)["secret"][0]
    result = service.complete(
        challenge.challenge_token,
        totp_code(secret, int(NOW.timestamp()) // 30),
        "origin",
    )
    db.close()
    return secret, result


@pytest.mark.parametrize("role", ["ADMIN", "LOGISTICS_MANAGER"])
def test_sensitive_login_is_restricted_until_enrollment(client, session_factory, role):
    user = account(session_factory, role)
    response = client.post(
        BASE + "/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["purpose"] == "ENROLL"
    assert not client.cookies.get(settings.session_cookie_name)
    assert client.get(BASE + "/me").status_code == 401
    assert client.get("/api/v1/orders").status_code == 401
    token = response.json()["challenge_token"]
    uri = client.post(BASE + "/mfa/setup", json={"challenge_token": token}).json()[
        "provisioning_uri"
    ]
    secret = parse_qs(urlsplit(uri).query)["secret"][0]
    response = client.post(
        BASE + "/mfa/verify",
        json={
            "challenge_token": token,
            "code": totp_code(secret, int(datetime.now(UTC).timestamp()) // 30),
        },
    )
    assert response.status_code == 200
    assert len(response.json()["recovery_codes"]) == 10
    assert client.cookies.get(settings.session_cookie_name)
    assert client.get(BASE + "/me").json()["id"] == str(user.id)
    assert (
        client.post(
            BASE + "/mfa/verify",
            json={
                "challenge_token": token,
                "code": response.json()["recovery_codes"][0],
            },
        ).status_code
        == 400
    )


def test_recovery_neutral_and_fail_closed_without_provider(
    client, session_factory, monkeypatch
):
    import app.modules.auth.identity_router as router

    user = account(session_factory)
    deliveries = []

    class Fake:
        def deliver(self, email, token):
            deliveries.append((email, token))

    monkeypatch.setattr(router, "get_recovery_delivery", lambda: Fake())
    existing = client.post(BASE + "/password-recovery", json={"email": user.email})
    absent = client.post(
        BASE + "/password-recovery", json={"email": "missing@example.test"}
    )
    assert existing.status_code == absent.status_code == 202
    assert existing.json() == absent.json()
    assert len(deliveries) == 1
    assert deliveries[0][1] not in str(existing.json())
    with session_factory() as db:
        saved = db.scalar(select(AuthPasswordReset))
        assert saved.token_hash != deliveries[0][1]
    monkeypatch.undo()
    for email in (user.email, "missing@example.test"):
        assert (
            client.post(BASE + "/password-recovery", json={"email": email}).status_code
            == 503
        )


def test_reset_single_use_revokes_sessions_preserves_mfa(session_factory):
    user = account(session_factory)
    _, result = enrollment(session_factory, user)
    with session_factory() as db:
        recovery = PasswordRecoveryService(db, now_provider=lambda: NOW)
        _, token = recovery.request(user.email, "origin")
        recovery.confirm(token, NEW_PASSWORD, "origin")
        assert db.scalar(select(AuthFactor)).enabled
        assert all(s.revoked_at for s in db.scalars(select(AuthSession)).all())
        with pytest.raises(ApiError, match="Link inválido"):
            recovery.confirm(token, NEW_PASSWORD, "origin")
        assert result.session.token != token


@pytest.mark.parametrize("expired", [False, True])
def test_reset_invalid_expired_and_replaced(session_factory, expired):
    user = account(session_factory, "CHECKER")
    with session_factory() as db:
        service = PasswordRecoveryService(db, now_provider=lambda: NOW)
        _, old = service.request(user.email, "origin")
        _, new = service.request(user.email, "origin")
        with pytest.raises(ApiError):
            service.confirm(old, NEW_PASSWORD, "origin")
        if expired:
            service.now = lambda: NOW + timedelta(minutes=16)
            with pytest.raises(ApiError):
                service.confirm(new, NEW_PASSWORD, "origin")
        else:
            service.confirm(new, NEW_PASSWORD, "origin")
        with pytest.raises(ApiError):
            service.confirm("invalid", NEW_PASSWORD, "different")


def test_mfa_replay_recovery_and_exhaustion(session_factory):
    user = account(session_factory)
    secret, first = enrollment(session_factory, user)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW)
        challenge = service.begin(user, expected_hash=user.password_hash)
        reused_code = totp_code(secret, int(NOW.timestamp()) // 30)
        with pytest.raises(ApiError):
            service.complete(challenge.challenge_token, reused_code, "origin")
        second = service.complete(
            challenge.challenge_token, first.recovery_codes[0], "origin"
        )
        assert second.recovery_codes == []
        challenge = service.begin(user, expected_hash=user.password_hash)
        with pytest.raises(ApiError):
            service.complete(
                challenge.challenge_token, first.recovery_codes[0], "origin"
            )
        for code in first.recovery_codes[1:]:
            challenge = service.begin(user, expected_hash=user.password_hash)
            service.complete(challenge.challenge_token, code, "origin")
        assert all(
            code.consumed_at for code in db.scalars(select(AuthRecoveryCode)).all()
        )


def test_challenge_expiration_budget_and_password_invalidation(session_factory):
    user = account(session_factory)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW)
        challenge = service.begin(user, expected_hash=user.password_hash)
        service.now = lambda: NOW + timedelta(minutes=6)
        with pytest.raises(ApiError):
            service.setup(challenge.challenge_token, "origin")
        service.now = lambda: NOW
        challenge = service.begin(user, expected_hash=user.password_hash)
        for _ in range(5):
            with pytest.raises(ApiError):
                service.complete(challenge.challenge_token, "000000", "origin")
        assert (
            db.scalar(
                select(AuthChallenge)
                .where(AuthChallenge.token_hash.is_not(None))
                .order_by(AuthChallenge.created_at.desc(), AuthChallenge.id)
            ).failed_count
            >= 0
        )
        assert any(
            item.failed_count == 5 and item.consumed_at
            for item in db.scalars(select(AuthChallenge)).all()
        )
        challenge = service.begin(user, expected_hash=user.password_hash)
        UserService(db).update_user(user.id, UserUpdate(password=NEW_PASSWORD))
        with pytest.raises(ApiError):
            service.setup(challenge.challenge_token, "another-origin")


def test_manage_requires_password_factor_csrf_and_revokes(client, session_factory):
    user = account(session_factory)
    _, first = enrollment(session_factory, user)
    headers = issue_session_headers(session_factory, user.id)
    assert (
        client.post(
            BASE + "/me/mfa/recovery-codes",
            headers={"Cookie": headers["Cookie"]},
            json={"password": PASSWORD, "code": first.recovery_codes[0]},
        ).status_code
        == 403
    )
    assert (
        client.post(
            BASE + "/me/mfa/recovery-codes",
            headers=headers,
            json={"password": "wrong", "code": first.recovery_codes[0]},
        ).status_code
        == 400
    )
    response = client.post(
        BASE + "/me/mfa/recovery-codes",
        headers=headers,
        json={"password": PASSWORD, "code": first.recovery_codes[0]},
    )
    assert response.status_code == 200
    assert len(response.json()["recovery_codes"]) == 10
    code = response.json()["recovery_codes"][0]
    assert (
        client.post(
            BASE + "/me/mfa/disable",
            headers=headers,
            json={"password": PASSWORD, "code": code},
        ).status_code
        == 204
    )
    assert client.get(BASE + "/me", headers=headers).status_code == 401
    assert (
        client.post(
            BASE + "/login", json={"email": user.email, "password": PASSWORD}
        ).json()["purpose"]
        == "ENROLL"
    )


def test_challenge_invalidated_by_revocation_and_logs_sanitized(
    session_factory, caplog
):
    user = account(session_factory)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW)
        challenge = service.begin(user, expected_hash=user.password_hash)
        AuthSessionService(db).revoke_all_for_user(user.id)
        with pytest.raises(ApiError):
            service.setup(challenge.challenge_token, "origin")
        assert challenge.challenge_token not in caplog.text
        assert user.email not in caplog.text
        assert PASSWORD not in caplog.text


def test_profile_email_cannot_hijack_recovery_without_second_factor(
    client, session_factory
):
    user = account(session_factory)
    _, first = enrollment(session_factory, user)
    headers = issue_session_headers(session_factory, user.id)
    response = client.patch(
        BASE + "/me",
        headers=headers,
        json={"name": user.name, "email": "new@example.test"},
    )
    assert response.status_code == 400
    assert client.get(BASE + "/me", headers=headers).json()["email"] == user.email
    response = client.patch(
        BASE + "/me",
        headers=headers,
        json={
            "name": user.name,
            "email": "new@example.test",
            "current_password": PASSWORD,
            "second_factor": first.recovery_codes[0],
        },
    )
    assert response.status_code == 200


def test_recovery_and_mfa_roll_back_when_audit_fails(session_factory, monkeypatch):
    from app.core.security import verify_password
    from app.modules.status_history.service import AuditService

    user = account(session_factory)

    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    with session_factory() as db:
        identity = IdentityService(db, now_provider=lambda: NOW)
        challenge = identity.begin(user, expected_hash=user.password_hash)
        uri = identity.setup(challenge.challenge_token, "origin")
        secret = parse_qs(urlsplit(uri).query)["secret"][0]
        recovery = PasswordRecoveryService(db, now_provider=lambda: NOW)
        _, token = recovery.request(user.email, "rollback")
        monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
        valid_code = totp_code(secret, int(NOW.timestamp()) // 30)
        with pytest.raises(RuntimeError):
            identity.complete(challenge.challenge_token, valid_code, "origin")
        db.rollback()
        assert not db.scalar(select(AuthFactor)).enabled
        assert db.scalar(select(AuthChallenge)).consumed_at is None
        assert list(db.scalars(select(AuthSession))) == []
        with pytest.raises(RuntimeError):
            recovery.confirm(token, NEW_PASSWORD, "rollback")
        db.rollback()
        assert db.scalar(select(AuthPasswordReset)).consumed_at is None
        assert verify_password(
            PASSWORD, UserService(db).get_user(user.id).password_hash
        )


@pytest.mark.parametrize("kind", ["reset", "mfa"])
def test_concurrent_consumption_has_exactly_one_winner(postgres_engine, kind):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from app.modules.auth.throttling import AuthRateLimitedError
    from app.modules.status_history.models import AuditEvent
    from app.modules.users.models import User

    with Session(postgres_engine) as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Concorrência fictícia",
                email=f"concurrent-{kind}@example.test",
                password=PASSWORD,
                role="ADMIN",
            )
        )
        if kind == "reset":
            _, token = PasswordRecoveryService(db, now_provider=lambda: NOW).request(
                user.email, "race-reset"
            )
            code = ""
        else:
            identity = IdentityService(db, now_provider=lambda: NOW)
            challenge = identity.begin(user, expected_hash=user.password_hash)
            token = challenge.challenge_token
            uri = identity.setup(token, "race-mfa")
            code = totp_code(
                parse_qs(urlsplit(uri).query)["secret"][0], int(NOW.timestamp()) // 30
            )
        user_id = user.id
    barrier = Barrier(2)

    def consume():
        with Session(postgres_engine) as db:
            barrier.wait(timeout=10)
            try:
                if kind == "reset":
                    PasswordRecoveryService(db, now_provider=lambda: NOW).confirm(
                        token, NEW_PASSWORD, "race-reset"
                    )
                else:
                    IdentityService(db, now_provider=lambda: NOW).complete(
                        token, code, "race-mfa"
                    )
                return "success"
            except (ApiError, AuthRateLimitedError):
                db.rollback()
                return "rejected"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: consume(), range(2)))
        assert sorted(results) == ["rejected", "success"]
        with Session(postgres_engine) as db:
            sessions = list(
                db.scalars(select(AuthSession).where(AuthSession.user_id == user_id))
            )
            assert len(sessions) == (1 if kind == "mfa" else 0)
    finally:
        with Session(postgres_engine) as db:
            db.execute(delete(AuditEvent).where(AuditEvent.entity_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.commit()


@pytest.mark.parametrize(
    "path", ["/me/mfa", "/me/mfa/enroll", "/me/mfa/recovery-codes", "/me/mfa/disable"]
)
def test_mfa_management_requires_auth(client, path):
    response = (
        client.get(BASE + path)
        if path == "/me/mfa"
        else client.post(BASE + path, json={"password": PASSWORD, "code": "123456"})
    )
    assert response.status_code == 401


def test_recovery_requests_are_durably_limited(client, session_factory, monkeypatch):
    import app.modules.auth.identity_router as router

    class Fake:
        def deliver(self, email, token):
            pass

    monkeypatch.setattr(router, "get_recovery_delivery", lambda: Fake())
    for _ in range(5):
        assert (
            client.post(
                BASE + "/password-recovery", json={"email": "unknown@example.test"}
            ).status_code
            == 202
        )
    response = client.post(
        BASE + "/password-recovery", json={"email": "unknown@example.test"}
    )
    assert response.status_code == 429
    assert response.headers["retry-after"]


def test_mfa_rejection_budget_survives_new_challenges(session_factory):
    from app.modules.auth.throttling import AuthRateLimitedError

    user = account(session_factory)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW)
        for _ in range(5):
            challenge = service.begin(user, expected_hash=user.password_hash)
            with pytest.raises(ApiError):
                service.complete(challenge.challenge_token, "invalid-code", "budget")
        challenge = service.begin(user, expected_hash=user.password_hash)
        with pytest.raises(AuthRateLimitedError):
            service.complete(challenge.challenge_token, "invalid-code", "budget")


def test_voluntary_enrollment_ends_old_full_session(client, session_factory):
    user = account(session_factory, "CHECKER")
    headers = issue_session_headers(session_factory, user.id)
    response = client.post(
        BASE + "/me/mfa/enroll", headers=headers, json={"password": PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["purpose"] == "ENROLL"
    assert client.get(BASE + "/me", headers=headers).status_code == 401
    assert (
        client.post(
            BASE + "/mfa/setup",
            json={"challenge_token": response.json()["challenge_token"]},
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "change", [{"password": NEW_PASSWORD}, {"email": "changed@example.test"}]
)
def test_account_identity_change_invalidates_existing_reset(session_factory, change):
    user = account(session_factory)
    with session_factory() as db:
        recovery = PasswordRecoveryService(db, now_provider=lambda: NOW)
        _, token = recovery.request(user.email, "identity-change")
        UserService(db).update_user(user.id, UserUpdate(**change))
        with pytest.raises(ApiError):
            recovery.confirm(token, NEW_PASSWORD, "identity-change")


def test_recovery_code_audit_does_not_claim_consumption_on_rollback(
    session_factory, monkeypatch, caplog
):
    from app.modules.status_history.service import AuditService

    user = account(session_factory)
    _, first = enrollment(session_factory, user)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW)
        current = service.sessions.resolve_session(first.session.token)

        def fail(*args, **kwargs):
            raise RuntimeError("audit unavailable")

        monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
        caplog.clear()
        with pytest.raises(RuntimeError):
            service.manage(
                current, PASSWORD, first.recovery_codes[0], "regenerate", "origin"
            )
        db.rollback()
        assert all(
            code.consumed_at is None for code in db.scalars(select(AuthRecoveryCode))
        )
        assert "AUTH_MFA_RECOVERY_USED" not in caplog.text


def test_only_completed_mfa_resets_authentication_failure_budgets(session_factory):
    from app.modules.auth.models import AuthLoginThrottle
    from app.modules.auth.throttling import LoginThrottleService

    user = account(session_factory)
    with session_factory() as db:
        throttle = LoginThrottleService(db, now_provider=lambda: NOW)
        for _ in range(4):
            throttle.record_failed_login(user.email, "origin")
        identity = IdentityService(db, now_provider=lambda: NOW)
        challenge = identity.begin(user, expected_hash=user.password_hash)
        assert all(
            row.failed_count == 4 for row in db.scalars(select(AuthLoginThrottle))
        )
        uri = identity.setup(challenge.challenge_token, "origin")
        secret = parse_qs(urlsplit(uri).query)["secret"][0]
        identity.complete(
            challenge.challenge_token,
            totp_code(secret, int(NOW.timestamp()) // 30),
            "origin",
        )
        assert list(db.scalars(select(AuthLoginThrottle))) == []
