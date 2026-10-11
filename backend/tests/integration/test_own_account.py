import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import verify_and_update_password
from app.modules.auth.models import AuthSession
from app.modules.auth.sessions import AuthSessionInvalidError, AuthSessionService
from app.modules.status_history.service import AuditService
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers

PASSWORD = "Senha-ficticia-segura-2026"
NEW_PASSWORD = "Nova-senha-ficticia-2026"
BASE = "/api/v1/auth/me"


def account(factory, role="ADMIN", email="conta@example.test"):
    with factory() as db:
        return UserService(db).create_user(
            UserCreate(name="Conta Fictícia", email=email, password=PASSWORD, role=role)
        )


@pytest.mark.parametrize("role", ["ADMIN", "LOGISTICS_MANAGER", "CHECKER", "DRIVER"])
def test_all_roles_read_update_and_persist_profile(client, session_factory, role):
    user = account(session_factory, role)
    headers = issue_session_headers(session_factory, user.id)
    original = client.get(BASE, headers=headers)
    assert original.status_code == 200
    assert not {"password", "password_hash", "token"} & original.json().keys()
    response = client.patch(
        BASE,
        headers=headers,
        json={"name": " Novo Nome ", "email": " NOVO@EXAMPLE.TEST "},
    )
    assert response.status_code == 200
    assert response.json()["role"] == role
    assert response.json()["email"] == "novo@example.test"
    assert client.get(BASE, headers=headers).json()["name"] == "Novo Nome"
    assert client.get(BASE + "/sessions", headers=headers).status_code == 200


@pytest.mark.parametrize(
    "field,value",
    [
        ("role", "ADMIN"),
        ("active", False),
        ("driver_id", None),
        ("password", NEW_PASSWORD),
        ("id", str(uuid.uuid4())),
    ],
)
def test_cannot_change_security_fields(client, session_factory, field, value):
    user = account(session_factory, "CHECKER")
    headers = issue_session_headers(session_factory, user.id)
    response = client.patch(
        BASE, headers=headers, json={"name": "Outro", "email": user.email, field: value}
    )
    assert response.status_code == 422
    assert client.get(BASE, headers=headers).json()["role"] == "CHECKER"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": " ", "email": "a@example.test"},
        {"name": "Nome", "email": "inválido"},
        {"name": None, "email": "a@example.test"},
    ],
)
def test_profile_validation(client, session_factory, payload):
    user = account(session_factory)
    assert (
        client.patch(
            BASE, json=payload, headers=issue_session_headers(session_factory, user.id)
        ).status_code
        == 422
    )


def test_duplicate_email(client, session_factory):
    user = account(session_factory)
    other = account(session_factory, email="outra@example.test")
    headers = issue_session_headers(session_factory, user.id)
    assert (
        client.patch(
            BASE, headers=headers, json={"name": "Nome", "email": other.email}
        ).status_code
        == 409
    )
    assert client.get(BASE, headers=headers).json()["email"] == user.email


def test_password_change_revokes_every_session_and_requires_login(
    client, session_factory, caplog
):
    user = account(session_factory)
    current = issue_session_headers(session_factory, user.id)
    other = issue_session_headers(session_factory, user.id)
    response = client.post(
        BASE + "/password",
        headers=current,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]
    for headers in (current, other):
        assert client.get(BASE, headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": NEW_PASSWORD}
        ).status_code
        == 200
    )
    assert PASSWORD not in caplog.text
    assert NEW_PASSWORD not in caplog.text
    assert user.email not in caplog.text


@pytest.mark.parametrize("password", ["short", "a" * 129, "passwordpassword"])
def test_password_policy_rejects_and_keeps_session(client, session_factory, password):
    user = account(session_factory)
    headers = issue_session_headers(session_factory, user.id)
    assert (
        client.post(
            BASE + "/password",
            headers=headers,
            json={"current_password": PASSWORD, "new_password": password},
        ).status_code
        == 422
    )
    assert client.get(BASE, headers=headers).status_code == 200


def test_wrong_password_and_existing_throttle(client, session_factory):
    user = account(session_factory)
    headers = issue_session_headers(session_factory, user.id)
    for _ in range(5):
        response = client.post(
            BASE + "/password",
            headers=headers,
            json={"current_password": "wrong", "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "AUTH_CURRENT_PASSWORD_INVALID"
    blocked = client.post(
        BASE + "/password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert blocked.status_code == 429
    assert blocked.headers['retry-after']
    assert client.get(BASE, headers=headers).status_code == 200


def test_session_list_real_metadata_excludes_expired_and_foreign(
    client, session_factory
):
    user = account(session_factory)
    other = account(session_factory, email="outra@example.test")
    headers = issue_session_headers(session_factory, user.id)
    issue_session_headers(session_factory, user.id)
    issue_session_headers(session_factory, other.id)
    with session_factory() as db:
        expired = AuthSessionService(db).create_session(user.id).auth_session
        expired_id = expired.id
        expired.idle_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    rows = client.get(BASE + "/sessions", headers=headers).json()
    assert len(rows) == 2
    assert sum((row['current'] for row in rows)) == 1
    assert all(
        set(row)
        == {
            "id",
            "created_at",
            "last_seen_at",
            "idle_expires_at",
            "absolute_expires_at",
            "current",
        }
        for row in rows
    )
    assert str(expired_id) not in str(rows)


def test_revoke_other_and_current_sessions(client, session_factory):
    user = account(session_factory)
    current = issue_session_headers(session_factory, user.id)
    other = issue_session_headers(session_factory, user.id)
    rows = client.get(BASE + "/sessions", headers=current).json()
    other_id = next(row["id"] for row in rows if not row["current"])
    assert (
        client.delete(BASE + "/sessions/" + other_id, headers=current).status_code
        == 204
    )
    assert client.get(BASE, headers=other).status_code == 401
    current_id = next(row["id"] for row in rows if row["current"])
    response = client.delete(BASE + "/sessions/" + current_id, headers=current)
    assert response.status_code == 204
    assert 'Max-Age=0' in response.headers['set-cookie']
    assert client.get(BASE, headers=current).status_code == 401


def test_revoke_others_preserves_current_and_foreign(client, session_factory):
    user = account(session_factory)
    foreign = account(session_factory, email="foreign@example.test")
    current = issue_session_headers(session_factory, user.id)
    other = issue_session_headers(session_factory, user.id)
    foreign_headers = issue_session_headers(session_factory, foreign.id)
    assert (
        client.post(BASE + "/sessions/revoke-others", headers=current).status_code
        == 204
    )
    assert client.get(BASE, headers=current).status_code == 200
    assert client.get(BASE, headers=other).status_code == 401
    assert client.get(BASE, headers=foreign_headers).status_code == 200
    assert (
        client.post(BASE + "/sessions/revoke-others", headers=current).status_code
        == 204
    )


def test_cannot_revoke_foreign_or_unknown_session(client, session_factory):
    user = account(session_factory)
    other = account(session_factory, email="other@example.test")
    headers = issue_session_headers(session_factory, user.id)
    foreign = issue_session_headers(session_factory, other.id)
    foreign_id = client.get(BASE + "/sessions", headers=foreign).json()[0]["id"]
    for session_id in (foreign_id, str(uuid.uuid4())):
        response = client.delete(BASE + "/sessions/" + session_id, headers=headers)
        assert response.status_code == 404
        assert response.json()['code'] == 'AUTH_SESSION_NOT_FOUND'
    assert client.get(BASE, headers=foreign).status_code == 200


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("patch", BASE, {"name": "Nome", "email": "a@example.test"}),
        (
            "post",
            BASE + "/password",
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        ),
        ("post", BASE + "/sessions/revoke-others", None),
        ("delete", BASE + "/sessions/" + str(uuid.uuid4()), None),
    ],
)
def test_unsafe_operations_require_auth_csrf_and_origin(
    client, session_factory, method, path, payload
):
    call = getattr(client, method)
    kwargs = {"json": payload} if payload is not None else {}
    assert call(path, **kwargs).status_code == 401
    user = account(session_factory)
    headers = issue_session_headers(session_factory, user.id)
    cookie_only = {"Cookie": headers["Cookie"]}
    assert call(path, headers=cookie_only, **kwargs).status_code == 403
    assert (
        call(
            path, headers={**headers, "Origin": "https://evil.example.test"}, **kwargs
        ).status_code
        == 403
    )


def test_password_and_revocation_roll_back_when_audit_fails(
    client, session_factory, monkeypatch
):
    user = account(session_factory)
    headers = issue_session_headers(session_factory, user.id)

    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
    response = client.post(
        BASE + "/password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 500
    assert "audit unavailable" not in response.text
    with session_factory() as db:
        stored = UserService(db).get_user(user.id)
        assert verify_and_update_password(PASSWORD, stored.password_hash)[0]
        assert all(s.revoked_at is None for s in db.scalars(select(AuthSession)))
    assert client.get(BASE, headers=headers).status_code == 200


def test_stale_login_cannot_issue_session_after_password_change(session_factory):
    user = account(session_factory)
    with session_factory() as db:
        old_hash = UserService(db).get_user(user.id).password_hash
        from app.modules.users.schemas import UserUpdate

        UserService(db).update_user(user.id, UserUpdate(password=NEW_PASSWORD))
    with session_factory() as db:
        service = AuthSessionService(db)
        with pytest.raises(AuthSessionInvalidError):
            service.create_session(user.id, expected_password_hash=old_hash)
        assert list(db.scalars(select(AuthSession))) == []


def test_profile_audit_contains_fields_without_values(client, session_factory, caplog):
    from app.modules.status_history.models import AuditEvent

    user = account(session_factory)
    headers = issue_session_headers(session_factory, user.id)
    with caplog.at_level("INFO", logger="loadx.security"):
        assert (
            client.patch(
                BASE,
                headers=headers,
                json={"name": "Atualizado", "email": "novo@example.test"},
            ).status_code
            == 200
        )
    assert "AUTH_OWN_PROFILE_UPDATED" in caplog.text
    assert "novo@example.test" not in caplog.text
    with session_factory() as db:
        event = db.scalars(select(AuditEvent)).one()
        assert event.actor_id == user.id
        assert event.entity_id == user.id
        assert event.changed_fields == "email,name"
        assert "novo@example.test" not in str(event.__dict__)


def test_session_queries_require_auth_and_invalid_uuid_is_rejected(
    client, session_factory
):
    assert client.get(BASE + "/sessions").status_code == 401
    user = account(session_factory)
    headers = issue_session_headers(session_factory, user.id)
    assert (
        client.delete(BASE + "/sessions/not-a-uuid", headers=headers).status_code == 422
    )


def test_session_revoked_after_resolution_cannot_mutate_account(session_factory):
    from app.modules.auth.account_service import AccountService
    from app.modules.auth.schemas import OwnProfileUpdate

    user = account(session_factory)
    with session_factory() as db:
        session_service = AuthSessionService(db)
        issued = session_service.create_session(user.id)
        current = session_service.resolve_session(issued.token)
        session_service.revoke_all_for_user(user.id)
        service = AccountService(db)
        data = OwnProfileUpdate(name="Negado", email=user.email)
        with pytest.raises(AuthSessionInvalidError):
            service.update_profile(current, data)
        assert UserService(db).get_user(user.id).name == "Conta Fictícia"
