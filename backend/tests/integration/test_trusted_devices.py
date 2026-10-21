import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.config import settings
from app.core.exceptions import ApiError
from app.modules.auth.identity_service import IdentityService, MfaChallengeResult
from app.modules.auth.models import (
    AuthChallenge,
    AuthFactor,
    AuthSession,
    AuthTrustedDevice,
)
from app.modules.auth.recovery_service import PasswordRecoveryService
from app.modules.auth.schemas import AuthLogin
from app.modules.auth.service import AuthInvalidCredentialsError, AuthService
from app.modules.auth.sessions import AuthSessionService, AuthTrustedDeviceRequiredError
from app.modules.auth.totp import IdentityUnavailableError, totp_code
from app.modules.auth.trusted_device_repository import TrustedDeviceRepository
from app.modules.auth.trusted_device_service import TrustedDeviceService, token_digest
from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers

NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)
PASSWORD = "Frase ficticia de acesso segura 2026!"
NEW_PASSWORD = "Outra frase ficticia muito segura 2026!"
BASE = "/api/v1/auth"


@pytest.fixture(autouse=True)
def enable_trust(monkeypatch):
    monkeypatch.setattr(settings, "trusted_devices_enabled", True)
    monkeypatch.setattr(settings, "trusted_device_days", 30)


def create_account(factory, role="LOGISTICS_MANAGER", suffix=""):
    with factory() as db:
        return UserService(db).create_user(
            UserCreate(
                name="Conta fictícia",
                email=f"trust{suffix}@example.test",
                password=PASSWORD,
                role=role,
            )
        )


def enroll(factory, user):
    with factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW)
        challenge = service.begin(user, expected_hash=user.password_hash)
        uri = service.setup(challenge.challenge_token, "origin")
        secret = parse_qs(urlsplit(uri).query)["secret"][0]
        result = service.complete(
            challenge.challenge_token,
            totp_code(secret, int(NOW.timestamp()) // 30),
            "origin",
            trust_device=True,
        )
        assert (
            result.trusted_device is None
        )  # Never first enrollment, even a forged opt-in.
        return secret, result


def trust(factory, user, secret, at=NOW + timedelta(seconds=30), previous=None):
    with factory() as db:
        service = IdentityService(db, now_provider=lambda: at)
        challenge = service.begin(user, expected_hash=user.password_hash)
        result = service.complete(
            challenge.challenge_token,
            totp_code(secret, int(at.timestamp()) // 30),
            "origin",
            trust_device=True,
            previous_device_token=previous,
        )
        assert result.trusted_device is not None
        return result.trusted_device


def password_login(factory, user, token=None):
    with factory() as db:
        return AuthService(db).login(
            AuthLogin(email=user.email, password=PASSWORD),
            "login-origin",
            trusted_device_token=token,
        )


def test_opt_in_only_after_totp_login_and_token_not_persisted(session_factory, caplog):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW + timedelta(seconds=30))
        challenge = service.begin(user, expected_hash=user.password_hash)
        result = service.complete(
            challenge.challenge_token,
            totp_code(secret, int((NOW + timedelta(seconds=30)).timestamp()) // 30),
            "origin",
        )
        assert result.trusted_device is None
        assert db.scalar(select(func.count()).select_from(AuthTrustedDevice)) == 0
    issued = trust(session_factory, user, secret, NOW + timedelta(seconds=60))
    assert len(issued.token) >= 43
    with session_factory() as db:
        record = db.get(AuthTrustedDevice, issued.device.id)
        assert record.token_hash == token_digest(issued.token)
        assert record.token_hash != issued.token
        assert record.expires_at - record.created_at == timedelta(days=30)
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.changed_fields.contains("trusted_device_created"))
            )
            == 1
        )
    assert issued.token not in caplog.text
    assert secret not in caplog.text


def test_recovery_code_cannot_create_trust(session_factory):
    user = create_account(session_factory)
    _, enrolled = enroll(session_factory, user)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW + timedelta(seconds=30))
        challenge = service.begin(user, expected_hash=user.password_hash)
        result = service.complete(
            challenge.challenge_token,
            enrolled.recovery_codes[0],
            "origin",
            trust_device=True,
        )
        assert result.trusted_device is None
        assert db.scalar(select(func.count()).select_from(AuthTrustedDevice)) == 0


@pytest.mark.parametrize(
    "kind",
    [
        "absent",
        "tampered",
        "other-account",
        "revoked",
        "disabled-flag",
        "factor-disabled",
        "changed-binding",
        "future-created",
    ],
)
def test_untrusted_context_requires_mfa(session_factory, monkeypatch, kind):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    token = issued.token
    if kind == "absent":
        token = None
    if kind == "tampered":
        token = ("y" if token[0] == "x" else "x") + token[1:]
        assert token != issued.token
    if kind == "other-account":
        user = create_account(session_factory, suffix="other")
        enroll(session_factory, user)
    if kind == "disabled-flag":
        monkeypatch.setattr(settings, "trusted_devices_enabled", False)
    with session_factory() as db:
        if kind == "revoked":
            db.get(AuthTrustedDevice, issued.device.id).revoked_at = NOW + timedelta(
                minutes=1
            )
        if kind == "factor-disabled":
            db.scalar(select(AuthFactor)).enabled = False
        if kind == "future-created":
            device = db.get(AuthTrustedDevice, issued.device.id)
            device.created_at = datetime.now(UTC) + timedelta(days=1)
            device.last_used_at = device.created_at
            device.expires_at = device.created_at + timedelta(days=30)
        if kind == "changed-binding":
            db.get(AuthTrustedDevice, issued.device.id).security_binding = "0" * 64
        db.commit()
    assert isinstance(password_login(session_factory, user, token), MfaChallengeResult)


def test_valid_cookie_never_bypasses_wrong_password_or_inactive_user(session_factory):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    with session_factory() as db:
        service = AuthService(db)
        invalid = AuthLogin(email=user.email, password="incorrect")
        with pytest.raises(AuthInvalidCredentialsError):
            service.login(
                invalid,
                "wrong",
                trusted_device_token=issued.token,
            )
        UserService(db).update_user(user.id, UserUpdate(active=False))
    with pytest.raises(AuthInvalidCredentialsError):
        password_login(session_factory, user, issued.token)


def test_trust_survives_other_browser_login_but_never_extends_session_or_device(
    session_factory,
):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    assert isinstance(password_login(session_factory, user), MfaChallengeResult)
    result = password_login(session_factory, user, issued.token)
    assert not isinstance(result, MfaChallengeResult)
    with session_factory() as db:
        session = db.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == token_digest(result.session.token)
            )
        )
        assert session.idle_expires_at - session.created_at == timedelta(minutes=30)
        assert session.absolute_expires_at - session.created_at == timedelta(hours=8)
        assert (
            db.get(AuthTrustedDevice, issued.device.id).expires_at
            == issued.device.expires_at
        )
        AuthSessionService(db).revoke_session(result.session.token)
    assert not isinstance(
        password_login(session_factory, user, issued.token), MfaChallengeResult
    )


@pytest.mark.parametrize(
    "offset,valid",
    [
        (timedelta(days=30, microseconds=-1), True),
        (timedelta(days=30), False),
        (timedelta(days=31), False),
    ],
)
def test_absolute_expiration_boundary(session_factory, offset, valid):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    with session_factory() as db:
        service = AuthSessionService(
            db, now_provider=lambda: issued.device.created_at + offset
        )
        kwargs = {
            "expected_password_hash": user.password_hash,
            "password_only": True,
            "trusted_device_token": issued.token,
        }
        if valid:
            service.create_session(user.id, **kwargs)
        else:
            with pytest.raises(AuthTrustedDeviceRequiredError):
                service.create_session(user.id, **kwargs)


@pytest.mark.parametrize(
    "change",
    ["password", "reset", "email", "role", "disable", "codes", "revoke-sessions"],
)
def test_security_mutations_revoke_devices(session_factory, change):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    with session_factory() as db:
        if change == "reset":
            service = PasswordRecoveryService(
                db, now_provider=lambda: NOW + timedelta(minutes=3)
            )
            _, token = service.request(user.email, "reset-origin")
            service.confirm(token, NEW_PASSWORD, "reset-origin")
        elif change in {"disable", "codes"}:
            sessions = AuthSessionService(
                db, now_provider=lambda: NOW + timedelta(minutes=1)
            )
            full = sessions.create_session(user.id)
            current = sessions.resolve_session(full.token)
            service = IdentityService(
                db, now_provider=lambda: NOW + timedelta(minutes=2)
            )
            service.manage(
                current,
                PASSWORD,
                totp_code(secret, int((NOW + timedelta(minutes=2)).timestamp()) // 30),
                "disable" if change == "disable" else "regenerate",
                "manage",
            )
        elif change == "revoke-sessions":
            AuthSessionService(db).revoke_all_for_user(user.id)
        else:
            data = (
                {"password": NEW_PASSWORD}
                if change == "password"
                else {"email": "new@example.test"}
                if change == "email"
                else {"role": "CHECKER"}
            )
            UserService(db).update_user(user.id, UserUpdate(**data), actor_id=user.id)
        assert db.get(AuthTrustedDevice, issued.device.id).revoked_at is not None


@pytest.mark.parametrize("forget_by_id", [False, True])
def test_login_cookie_lifecycle_management_origin_and_ownership(
    client, session_factory, forget_by_id
):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    # Current real clock is used by HTTP verification; enrollment's step is older.
    challenge = client.post(
        BASE + "/login", json={"email": user.email, "password": PASSWORD}
    ).json()
    assert challenge["trusted_device_days"] == 30
    response = client.post(
        BASE + "/mfa/verify",
        json={
            "challenge_token": challenge["challenge_token"],
            "code": totp_code(secret, int(datetime.now(UTC).timestamp()) // 30),
            "trust_device": True,
        },
    )
    assert response.status_code == 200
    cookie = response.headers.get_list("set-cookie")
    trusted_cookie = next(
        c for c in cookie if c.startswith(settings.trusted_device_cookie_name + "=")
    )
    for flag in ("HttpOnly", "SameSite=lax", "Path=/", "Max-Age=2592000"):
        assert flag in trusted_cookie
    assert "Domain=" not in trusted_cookie
    csrf = response.headers["X-CSRF-Token"]
    devices = client.get(BASE + "/me/trusted-devices").json()
    assert len(devices["items"]) == 1
    assert devices["items"][0]["current"]
    assert set(devices["items"][0]) == {
        "id",
        "created_at",
        "last_used_at",
        "expires_at",
        "current",
    }
    device_id = devices["items"][0]["id"]
    assert client.delete(BASE + "/me/trusted-devices/" + device_id).status_code == 403
    assert (
        client.delete(
            BASE + "/me/trusted-devices/" + device_id,
            headers={"X-CSRF-Token": csrf, "Origin": "https://evil.test"},
        ).status_code
        == 403
    )
    assert (
        client.post(BASE + "/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    )
    assert client.cookies.get(settings.trusted_device_cookie_name)
    response = client.post(
        BASE + "/login", json={"email": user.email, "password": PASSWORD}
    )
    assert "challenge_token" not in response.json()
    csrf = response.headers["X-CSRF-Token"]
    forget_path = device_id if forget_by_id else "current"
    assert (
        client.delete(
            BASE + "/me/trusted-devices/" + forget_path, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 204
    )
    assert client.cookies.get(settings.trusted_device_cookie_name) is None
    assert (
        client.post(BASE + "/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    )
    assert (
        client.post(
            BASE + "/login", json={"email": user.email, "password": PASSWORD}
        ).json()["purpose"]
        == "LOGIN"
    )


@pytest.mark.parametrize(
    "path,method",
    [
        ("", "get"),
        ("/current", "delete"),
        ("/revoke-all", "post"),
        ("/" + str(uuid.uuid4()), "delete"),
    ],
)
def test_management_rejects_missing_session(client, path, method):
    client.cookies.set(
        settings.trusted_device_cookie_name, "opaque-trust-is-not-a-session"
    )
    assert (
        getattr(client, method)(BASE + "/me/trusted-devices" + path).status_code == 401
    )


def test_other_user_cannot_revoke_device_and_revoke_all_is_idempotent(
    client, session_factory
):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    other = create_account(session_factory, "CHECKER", suffix="other")
    headers = issue_session_headers(session_factory, other.id)
    assert (
        client.delete(
            BASE + "/me/trusted-devices/" + str(issued.device.id), headers=headers
        ).status_code
        == 204
    )
    assert (
        client.get(BASE + "/me/trusted-devices", headers=headers).json()["items"] == []
    )
    with session_factory() as db:
        assert db.get(AuthTrustedDevice, issued.device.id).revoked_at is None
    headers = issue_session_headers(session_factory, user.id)
    for _ in range(2):
        assert (
            client.post(
                BASE + "/me/trusted-devices/revoke-all", headers=headers
            ).status_code
            == 204
        )
    with session_factory() as db:
        assert db.get(AuthTrustedDevice, issued.device.id).revoked_at is not None


def test_audit_failure_rolls_back_factor_session_and_credential(
    session_factory, monkeypatch
):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW + timedelta(seconds=30))
        challenge = service.begin(user, expected_hash=user.password_hash)
        count = db.scalar(select(func.count()).select_from(AuthSession))
        step = db.scalar(select(AuthFactor.last_totp_step))

        def fail(*args, **kwargs):
            raise RuntimeError("audit unavailable")

        monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
        code = totp_code(secret, int((NOW + timedelta(seconds=30)).timestamp()) // 30)
        with pytest.raises(RuntimeError):
            service.complete(
                challenge.challenge_token,
                code,
                "origin",
                trust_device=True,
            )
        db.rollback()
        assert db.scalar(select(func.count()).select_from(AuthTrustedDevice)) == 0
        assert db.scalar(select(func.count()).select_from(AuthSession)) == count
        assert db.scalar(select(AuthFactor.last_totp_step)) == step
        assert (
            db.scalar(
                select(AuthChallenge).where(
                    AuthChallenge.token_hash == token_digest(challenge.challenge_token)
                )
            ).consumed_at
            is None
        )


def test_storage_failure_fails_closed_without_session(session_factory, monkeypatch):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)

    def fail(*args, **kwargs):
        raise OperationalError("storage unavailable", {}, None)

    monkeypatch.setattr(TrustedDeviceRepository, "find", fail)
    with pytest.raises(IdentityUnavailableError):
        password_login(session_factory, user, issued.token)


@pytest.mark.parametrize("days", [0, 31])
def test_database_rejects_invalid_lifetime(session_factory, days):
    user = create_account(session_factory)
    with session_factory() as db:
        db.add(
            AuthTrustedDevice(
                user_id=user.id,
                token_hash="a" * 64,
                security_binding="b" * 64,
                created_at=NOW,
                last_used_at=NOW,
                expires_at=NOW + timedelta(days=days),
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()


def test_trusted_data_blocks_downgrade_without_deleting_identity(session_factory):
    from importlib import import_module

    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext

    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    with session_factory() as db:
        migration = import_module(
            "migrations.versions.20261021_0030_auth_trusted_devices"
        )
        with (
            Operations.context(MigrationContext.configure(db.connection())),
            pytest.raises(RuntimeError, match="downgrade blocked"),
        ):
            migration.downgrade()
        assert db.get(AuthTrustedDevice, issued.device.id) is not None
        assert db.scalar(select(AuthFactor)).enabled


def test_concurrent_opt_in_has_exactly_one_winner(postgres_engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from app.modules.auth.models import AuthLoginThrottle
    from app.modules.users.models import User

    factory = lambda: Session(postgres_engine)
    with factory() as db:
        prior = set(db.scalars(select(AuthLoginThrottle.id)))
    user = create_account(factory, suffix="race")
    secret, _ = enroll(factory, user)
    at = NOW + timedelta(seconds=30)
    with factory() as db:
        challenge = IdentityService(db, now_provider=lambda: at).begin(
            user, expected_hash=user.password_hash
        )
    barrier = Barrier(2)

    def complete():
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                IdentityService(db, now_provider=lambda: at).complete(
                    challenge.challenge_token,
                    totp_code(secret, int(at.timestamp()) // 30),
                    "race-trust",
                    trust_device=True,
                )
                return True
            except ApiError:
                db.rollback()
                return False

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: complete(), range(2)))
        assert sorted(results) == [False, True]
        with factory() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(AuthTrustedDevice)
                    .where(AuthTrustedDevice.user_id == user.id)
                )
                == 1
            )
    finally:
        with factory() as db:
            db.execute(delete(AuditEvent).where(AuditEvent.entity_id == user.id))
            db.execute(delete(User).where(User.id == user.id))
            db.execute(
                delete(AuthLoginThrottle).where(AuthLoginThrottle.id.not_in(prior))
            )
            db.commit()


def test_revocation_serializes_with_new_session(postgres_engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import delete
    from sqlalchemy.orm import Session

    from app.modules.auth.models import AuthLoginThrottle
    from app.modules.users.models import User

    factory = lambda: Session(postgres_engine)
    with factory() as db:
        prior = set(db.scalars(select(AuthLoginThrottle.id)))
    user = create_account(factory, suffix="revoke-race")
    secret, _ = enroll(factory, user)
    issued = trust(factory, user, secret)
    staged, started = Event(), Event()

    def revoke():
        with factory() as db:
            UserService(db).lock_account(user.id)
            TrustedDeviceRepository(db).revoke(user.id, datetime.now(UTC))
            staged.set()
            assert started.wait(10)
            db.commit()

    def authenticate():
        assert staged.wait(10)
        with factory() as db:
            started.set()
            service = AuthSessionService(db)
            with pytest.raises(AuthTrustedDeviceRequiredError):
                service.create_session(
                    user.id,
                    expected_password_hash=user.password_hash,
                    password_only=True,
                    trusted_device_token=issued.token,
                )
            db.rollback()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(revoke), executor.submit(authenticate)]
            for future in futures:
                future.result(timeout=15)
    finally:
        with factory() as db:
            db.execute(delete(AuditEvent).where(AuditEvent.entity_id == user.id))
            db.execute(delete(User).where(User.id == user.id))
            db.execute(
                delete(AuthLoginThrottle).where(AuthLoginThrottle.id.not_in(prior))
            )
            db.commit()


@pytest.mark.parametrize("role", ["ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER"])
def test_all_fixed_roles_can_use_and_revoke_only_own_trust(session_factory, role):
    user = create_account(session_factory, role)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    result = password_login(session_factory, user, issued.token)
    assert not isinstance(result, MfaChallengeResult)
    with session_factory() as db:
        current = AuthSessionService(db).resolve_session(result.session.token)
        service = TrustedDeviceService(db)
        assert service.list_own(current, issued.token).items[0].current
        service.revoke_own(current, all_devices=True)
    assert isinstance(
        password_login(session_factory, user, issued.token), MfaChallengeResult
    )


def test_custom_permissions_change_revokes_trust_and_preserves_mfa(session_factory):
    from app.modules.access_profiles.schemas import ProfileUpdate, ProfileWrite
    from app.modules.access_profiles.service import ProfileService

    user = create_account(session_factory, "ADMIN")
    with session_factory() as db:
        service = ProfileService(db)
        profile = service.save(
            ProfileWrite(name="Consulta fictícia", permissions=["loadx.trucks.read"]),
            actor_id=user.id,
        )
        custom = UserService(db).create_user(
            UserCreate(
                name="Conta personalizada",
                email="trust-custom@example.test",
                password=PASSWORD,
                role="CUSTOM",
                custom_profile_id=profile.id,
            )
        )
    secret, _ = enroll(session_factory, custom)
    issued = trust(session_factory, custom, secret)
    assert not isinstance(
        password_login(session_factory, custom, issued.token), MfaChallengeResult
    )
    with session_factory() as db:
        ProfileService(db).save(
            ProfileUpdate(
                name=profile.name,
                description="",
                active=True,
                permissions=["loadx.products.read"],
                version=profile.version,
            ),
            identity=profile.id,
            actor_id=user.id,
        )
        assert db.get(AuthTrustedDevice, issued.device.id).revoked_at is not None
        assert db.scalar(
            select(AuthFactor).where(AuthFactor.user_id == custom.id)
        ).enabled
    assert isinstance(
        password_login(session_factory, custom, issued.token), MfaChallengeResult
    )


def test_existing_cookie_does_not_authorize_sensitive_mfa_management(
    client, session_factory
):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    client.cookies.set(settings.trusted_device_cookie_name, issued.token)
    response = client.post(
        BASE + "/login", json={"email": user.email, "password": PASSWORD}
    )
    csrf = response.headers["X-CSRF-Token"]
    result = client.post(
        BASE + "/me/mfa/recovery-codes",
        json={"password": PASSWORD, "code": ""},
        headers={"X-CSRF-Token": csrf},
    )
    assert result.status_code == 400
    with session_factory() as db:
        assert db.get(AuthTrustedDevice, issued.device.id).revoked_at is None


def test_rate_limit_applies_before_trusted_bypass(client, session_factory):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    issued = trust(session_factory, user, secret)
    client.cookies.set(settings.trusted_device_cookie_name, issued.token)
    for _ in range(5):
        response = client.post(
            BASE + "/login", json={"email": user.email, "password": "incorrect"}
        )
    response = client.post(
        BASE + "/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 429
    assert response.headers.get("Retry-After")
    assert not client.cookies.get(settings.session_cookie_name)


def test_disabled_feature_and_flag_limits(session_factory, monkeypatch):
    from pydantic import ValidationError

    from app.core.config import Settings

    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    monkeypatch.setattr(settings, "trusted_devices_enabled", False)
    with session_factory() as db:
        service = IdentityService(db, now_provider=lambda: NOW + timedelta(seconds=30))
        challenge = service.begin(user, expected_hash=user.password_hash)
        assert challenge.trusted_device_days is None
        result = service.complete(
            challenge.challenge_token,
            totp_code(secret, int((NOW + timedelta(seconds=30)).timestamp()) // 30),
            "origin",
            trust_device=True,
        )
        assert result.trusted_device is None
    for days in [0, 31]:
        with pytest.raises(ValidationError):
            Settings(
                app_env="local",
                database_url=settings.database_url,
                trusted_device_days=days,
                _env_file=None,
            )


def test_production_cookie_is_host_only_secure_and_opt_in_is_strict(
    client, session_factory, monkeypatch
):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    monkeypatch.setattr(settings, "app_env", "production")
    response = client.post(
        BASE + "/login", json={"email": user.email, "password": PASSWORD}
    )
    challenge = response.json()["challenge_token"]
    body = {
        "challenge_token": challenge,
        "code": totp_code(secret, int(datetime.now(UTC).timestamp()) // 30),
        "trust_device": "true",
    }
    assert client.post(BASE + "/mfa/verify", json=body).status_code == 422
    body["trust_device"] = True
    response = client.post(BASE + "/mfa/verify", json=body)
    assert response.status_code == 200
    cookie = next(
        c
        for c in response.headers.get_list("set-cookie")
        if c.startswith("__Host-loadx_trusted_device=")
    )
    for flag in ("Secure", "HttpOnly", "Path=/"):
        assert flag in cookie
    assert "Domain=" not in cookie


def test_shorter_lifetime_and_rotation_preserve_other_browser(
    session_factory, monkeypatch
):
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    first = trust(session_factory, user, secret)
    second = trust(session_factory, user, secret, NOW + timedelta(seconds=60))
    monkeypatch.setattr(settings, "trusted_device_days", 7)
    third = trust(
        session_factory, user, secret, NOW + timedelta(seconds=90), previous=first.token
    )
    assert third.device.expires_at - third.device.created_at == timedelta(days=7)
    # A stale cookie used after another valid TOTP must not rewrite revocation history.
    trust(
        session_factory,
        user,
        secret,
        NOW + timedelta(seconds=120),
        previous=first.token,
    )
    with session_factory() as db:
        assert (
            db.get(AuthTrustedDevice, first.device.id).revoked_at
            == third.device.created_at
        )
        assert db.get(AuthTrustedDevice, first.device.id).revoked_at is not None
        assert db.get(AuthTrustedDevice, second.device.id).revoked_at is None
    assert not isinstance(
        password_login(session_factory, user, second.token), MfaChallengeResult
    )


def test_device_cap_revokes_oldest_and_keeps_history(session_factory, monkeypatch):
    monkeypatch.setattr("app.modules.auth.trusted_device_service.MAX_LIVE_DEVICES", 2)
    user = create_account(session_factory)
    secret, _ = enroll(session_factory, user)
    first = trust(session_factory, user, secret)
    second = trust(session_factory, user, secret, NOW + timedelta(seconds=60))
    third = trust(session_factory, user, secret, NOW + timedelta(seconds=90))
    with session_factory() as db:
        assert db.get(AuthTrustedDevice, first.device.id).revoked_at is not None
        assert db.get(AuthTrustedDevice, second.device.id).revoked_at is None
        assert db.get(AuthTrustedDevice, third.device.id).revoked_at is None
        assert db.scalar(select(func.count()).select_from(AuthTrustedDevice)) == 3
