import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import ApiError
from app.modules.access_profiles.catalog import CATALOG, SYSTEM_PERMISSIONS
from app.modules.access_profiles.models import AccessProfile, ProfilePermission
from app.modules.access_profiles.schemas import ProfileUpdate, ProfileWrite
from app.modules.access_profiles.service import ProfileService
from app.modules.auth.models import AuthSession
from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers

PASSWORD = "Frase ficticia de acesso 2026!"


@pytest.fixture
def administrator(session_factory):
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Admin perfis",
                email="profiles-admin@example.test",
                password=PASSWORD,
                role="ADMIN",
            )
        )
    return issue_session_headers(session_factory, user.id)


def proposal(**changes):
    return {
        "name": "Consulta de frota",
        "description": "Acesso restrito à frota",
        "active": True,
        "permissions": ["loadx.trucks.read"],
        **changes,
    }


def create_profile(client, administrator, **changes):
    result = client.post(
        "/api/v1/access-profiles", json=proposal(**changes), headers=administrator
    )
    assert result.status_code == 201, result.text
    return result.json()


def custom_user(client, administrator, profile):
    response = client.post(
        "/api/v1/users",
        headers=administrator,
        json={
            "name": "Operador fictício",
            "email": "custom@example.test",
            "password": PASSWORD,
            "role": "CUSTOM",
            "custom_profile_id": profile["id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "custom@example.test", "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response


def test_profiles_catalog_and_fixed_roles_after_migration(
    client, administrator, session_factory
):
    response = client.get("/api/v1/access-profiles", headers=administrator)
    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["system_role"] for item in items} == set(SYSTEM_PERMISSIONS)
    for item in items:
        assert set(item["permissions"]) == SYSTEM_PERMISSIONS[item["system_role"]]
        assert (
            client.patch(
                f"/api/v1/access-profiles/{item['id']}",
                headers=administrator,
                json={**proposal(), "version": 1},
            ).status_code
            == 404
        )
    catalog = client.get(
        "/api/v1/access-profiles/permissions", headers=administrator
    ).json()
    assert len(catalog) == len(CATALOG)
    assert all(item["code"].startswith("loadx.") for item in catalog)
    assert not any(
        "tenant" in item["code"] or "superadmin" in item["code"] for item in catalog
    )
    with session_factory() as db:
        assert db.scalar(text("SELECT count(*) FROM access_permissions")) == len(
            CATALOG
        )


@pytest.mark.parametrize("role", ["LOGISTICS_MANAGER", "CHECKER", "DRIVER"])
@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("GET", "", None),
        ("GET", "/permissions", None),
        ("POST", "", proposal()),
        ("PATCH", f"/{uuid.uuid4()}", {**proposal(), "version": 1}),
    ],
)
def test_non_admin_cannot_manage_profiles(
    client, session_factory, role, method, path, payload
):
    with session_factory() as db:
        user = UserService(db).create_user(
            UserCreate(
                name="Perfil fixo",
                email=f"{role}@example.test",
                password=PASSWORD,
                role=role,
            )
        )
    headers = issue_session_headers(session_factory, user.id)
    assert (
        client.request(
            method, f"/api/v1/access-profiles{path}", headers=headers, json=payload
        ).status_code
        == 403
    )


def test_profiles_require_authentication(client):
    assert client.get("/api/v1/access-profiles").status_code == 401
    assert client.get("/api/v1/access-profiles/permissions").status_code == 401


@pytest.mark.parametrize(
    "permissions",
    [
        ["loadx.users.manage"],
        ["loadx.profiles.manage"],
        ["loadx.settings.manage"],
        ["loadx.trips.own"],
        ["loadx.unknown.manage"],
        ["loadx.trucks.read", "loadx.trucks.read"],
    ],
)
def test_reserved_unknown_and_duplicate_grants_rejected(
    client, administrator, permissions
):
    response = client.post(
        "/api/v1/access-profiles",
        headers=administrator,
        json=proposal(permissions=permissions),
    )
    assert response.status_code == 422
    assert (
        client.get("/api/v1/access-profiles", headers=administrator).json()["total"]
        == 4
    )


def test_custom_profile_gates_real_resources_and_auth_projection(client, administrator):
    profile = create_profile(client, administrator)
    account = custom_user(client, administrator, profile)
    assert account["permissions"] == ["loadx.trucks.read"]
    auth = login(client)
    assert auth.json()["permissions"] == ["loadx.trucks.read"]
    assert (
        client.get("/api/v1/auth/me").json()["custom_profile_name"] == profile["name"]
    )
    assert client.get("/api/v1/trucks").status_code == 200
    assert client.get("/api/v1/products").status_code == 403
    assert client.get("/api/v1/customers").status_code == 403
    assert client.get("/api/v1/users").status_code == 403
    assert client.get("/api/v1/access-profiles").status_code == 403
    assert (
        client.post(
            "/api/v1/trucks",
            headers={"X-CSRF-Token": auth.headers["X-CSRF-Token"]},
            json={},
        ).status_code
        == 403
    )
    results = client.get("/api/v1/search", params={"search": "AB"})
    assert results.status_code == 200
    assert all(item["category"] == "truck" for item in results.json()["results"])


def test_profile_changes_revoke_sessions_and_are_audited(
    client, administrator, session_factory
):
    profile = create_profile(client, administrator)
    account = custom_user(client, administrator, profile)
    login(client)
    updated = client.patch(
        f"/api/v1/access-profiles/{profile['id']}",
        headers=administrator,
        json={
            **proposal(permissions=["loadx.products.read"]),
            "version": profile["version"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["user_count"] == 1
    assert client.get("/api/v1/auth/me").status_code == 401
    assert login(client).json()["permissions"] == ["loadx.products.read"]
    assert client.get("/api/v1/products").status_code == 200
    assert client.get("/api/v1/trucks").status_code == 403
    # An association update is a security change even when role stays CUSTOM.
    another = create_profile(client, administrator, name="Outra consulta")
    reassigned = client.patch(
        f"/api/v1/users/{account['id']}",
        headers=administrator,
        json={"custom_profile_id": another["id"]},
    )
    assert reassigned.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    with session_factory() as db:
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.entity_type == "ACCESS_PROFILE")
        ).all()
        assert {item.event_type for item in events} == {
            "PROFILE_CREATED",
            "PROFILE_UPDATED",
        }
        assert all("password" not in item.changed_fields for item in events)


def test_inactive_in_use_uniqueness_and_last_admin(client, administrator):
    profile = create_profile(client, administrator)
    assert (
        client.post(
            "/api/v1/access-profiles",
            headers=administrator,
            json=proposal(name="CONSULTA DE FROTA"),
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/access-profiles",
            headers=administrator,
            json=proposal(name="Administrador"),
        ).status_code
        == 409
    )
    account = custom_user(client, administrator, profile)
    assert (
        client.patch(
            f"/api/v1/access-profiles/{profile['id']}",
            headers=administrator,
            json={**proposal(active=False), "version": 1},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/users/{account['id']}",
            headers=administrator,
            json={"role": "CHECKER", "custom_profile_id": None},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/access-profiles/{profile['id']}",
            headers=administrator,
            json={**proposal(active=False), "version": 1},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/users/{account['id']}",
            headers=administrator,
            json={"role": "CUSTOM", "custom_profile_id": profile["id"]},
        ).status_code
        == 409
    )
    admin = client.get(
        "/api/v1/users", headers=administrator, params={"role": "ADMIN"}
    ).json()["items"][0]
    assert (
        client.patch(
            f"/api/v1/users/{admin['id']}",
            headers=administrator,
            json={"role": "CUSTOM", "custom_profile_id": profile["id"]},
        ).json()["code"]
        == "USER_LAST_ACTIVE_ADMIN_REQUIRED"
    )


@pytest.fixture
def concurrent_profiles(postgres_engine):
    factory = sessionmaker(bind=postgres_engine, autoflush=False)
    with factory() as db:
        admin = UserService(db).create_user(
            UserCreate(
                name="Concorrência OC112",
                email=f"{uuid.uuid4()}@example.test",
                password=PASSWORD,
                role="ADMIN",
            )
        )
        admin_id = admin.id
        profile = ProfileService(db).save(
            ProfileWrite(**proposal(name=f"Concorrência {uuid.uuid4()}")),
            actor_id=admin_id,
        )
    user_ids = [admin_id]
    try:
        yield factory, admin_id, profile, user_ids
    finally:
        with factory() as db:
            db.execute(delete(AuditEvent).where(AuditEvent.actor_id.in_(user_ids)))
            db.execute(delete(AuthSession).where(AuthSession.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.execute(
                delete(ProfilePermission).where(
                    ProfilePermission.profile_id == profile.id
                )
            )
            db.execute(delete(AccessProfile).where(AccessProfile.id == profile.id))
            db.execute(delete(User).where(User.id == admin_id))
            db.commit()


def test_concurrent_edits_use_version_and_preserve_single_solution(concurrent_profiles):
    factory, admin_id, profile, _user_ids = concurrent_profiles
    barrier = Barrier(2)

    def update(name):
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                ProfileService(db).save(
                    ProfileUpdate(**proposal(name=name), version=1),
                    actor_id=admin_id,
                    identity=profile.id,
                )
                return 200
            except ApiError as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(
            pool.map(update, [f"Edição A {profile.id}", f"Edição B {profile.id}"])
        )
    assert statuses == [200, 409]
    with factory() as db:
        assert ProfileService(db).get_profile(profile.id).version == 2


def test_failure_rolls_back_profile_grants_and_audit(
    client, administrator, monkeypatch
):
    profile = create_profile(client, administrator)
    custom_user(client, administrator, profile)
    login(client)

    def fail(*args, **kwargs):
        raise RuntimeError("falha simulada de auditoria")

    monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
    response = client.patch(
        f"/api/v1/access-profiles/{profile['id']}",
        headers=administrator,
        json={**proposal(permissions=["loadx.products.read"]), "version": 1},
    )
    assert response.status_code == 500
    assert client.get("/api/v1/auth/me").status_code == 200
    result = client.get(
        f"/api/v1/access-profiles/{profile['id']}", headers=administrator
    ).json()
    assert result["permissions"] == ["loadx.trucks.read"]
    assert result["version"] == 1


@pytest.mark.parametrize(
    "code,delegable",
    [
        ("loadx.users.manage", True),
        ("loadx.users.manage", False),
        ("loadx.unknown.manage", True),
    ],
)
def test_database_constraints_refuse_reserved_or_unknown_grants(
    client, administrator, session_factory, code, delegable
):
    profile = create_profile(client, administrator)
    with session_factory() as db:
        db.add(
            ProfilePermission(
                profile_id=uuid.UUID(profile["id"]),
                permission_code=code,
                delegable=delegable,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_database_normalized_unique_names_and_user_association(
    client, administrator, session_factory
):
    profile = create_profile(client, administrator)
    with session_factory() as db:
        db.add(
            AccessProfile(
                name="Outro", name_key="consulta de frota", description="", active=True
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        statement = text(
            "UPDATE users SET custom_profile_id=:profile WHERE role='ADMIN'"
        )
        with pytest.raises(IntegrityError):
            db.execute(
                statement,
                {"profile": profile["id"]},
            )
        db.rollback()


def test_profile_pagination_is_stable_and_bounded(client, administrator):
    create_profile(client, administrator)
    first = client.get(
        "/api/v1/access-profiles", headers=administrator, params={"page_size": 2}
    ).json()
    second = client.get(
        "/api/v1/access-profiles",
        headers=administrator,
        params={"page_size": 2, "page": 2},
    ).json()
    third = client.get(
        "/api/v1/access-profiles",
        headers=administrator,
        params={"page_size": 2, "page": 3},
    ).json()
    assert first["total"] == 5
    assert len(first["items"]) == len(second["items"]) == 2
    assert len(third["items"]) == 1
    assert (
        len({item["id"] for page in [first, second, third] for item in page["items"]})
        == 5
    )


def test_downgrade_refuses_to_discard_profile_identity_or_history(
    client, administrator, session_factory, monkeypatch
):
    from importlib import import_module

    profile = create_profile(client, administrator)
    migration = import_module("migrations.versions.20261016_0024_access_profiles")
    with session_factory() as db:
        monkeypatch.setattr(migration.op, "get_bind", lambda: db.connection())
        with pytest.raises(RuntimeError, match="history cannot be discarded"):
            migration.downgrade()
        assert db.get(AccessProfile, uuid.UUID(profile["id"])) is not None


def test_custom_profile_cannot_impersonate_driver_or_assign_reserved_role(
    client, administrator
):
    profile = create_profile(client, administrator, permissions=["loadx.trips.read"])
    custom_user(client, administrator, profile)
    auth = login(client)
    headers = {"X-CSRF-Token": auth.headers["X-CSRF-Token"]}
    assert (
        client.patch(
            "/api/v1/auth/me",
            headers=headers,
            json={"name": "Operador", "email": "custom@example.test", "role": "ADMIN"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "name": "Escalada",
                "email": "escalada@example.test",
                "role": "ADMIN",
                "password": PASSWORD,
            },
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/trips/{uuid.uuid4()}/status",
            headers=headers,
            json={"status": "IN_ROUTE"},
        ).status_code
        == 403
    )


def test_concurrent_admin_demotion_and_custom_assignment_preserve_last_admin(
    concurrent_profiles,
):
    factory, admin_id, profile, user_ids = concurrent_profiles
    with factory() as db:
        another = UserService(db).create_user(
            UserCreate(
                name="Outro admin",
                email=f"{uuid.uuid4()}@example.test",
                password=PASSWORD,
                role="ADMIN",
            )
        )
        user_ids.append(another.id)
    barrier = Barrier(2)

    def change(identity):
        data = (
            UserUpdate(role="CUSTOM", custom_profile_id=profile.id)
            if identity == admin_id
            else UserUpdate(role="CHECKER")
        )
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                UserService(db).update_user(identity, data, actor_id=admin_id)
                return "updated"
            except Exception as error:
                from app.modules.users.service import UserLastActiveAdminRequiredError

                if isinstance(error, UserLastActiveAdminRequiredError):
                    return "protected"
                raise

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(change, user_ids))
    assert results == ["protected", "updated"]
    with factory() as db:
        assert (
            db.scalar(
                select(text("count(*)"))
                .select_from(User)
                .where(User.role == "ADMIN", User.active.is_(True))
            )
            == 1
        )


def test_grant_change_revokes_all_members_with_one_session_query(
    client, administrator, session_factory
):
    from sqlalchemy import event

    profile = create_profile(client, administrator)
    headers = []
    for index in range(3):
        response = client.post(
            "/api/v1/users",
            headers=administrator,
            json={
                "name": f"Membro {index}",
                "email": f"membro{index}@example.test",
                "password": PASSWORD,
                "role": "CUSTOM",
                "custom_profile_id": profile["id"],
            },
        )
        assert response.status_code == 201
        headers.append(
            issue_session_headers(session_factory, uuid.UUID(response.json()["id"]))
        )
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        if "auth_sessions.user_id IN" in statement and statement.lstrip().startswith(
            "SELECT"
        ):
            statements.append(statement)

    with session_factory() as db:
        connection = db.get_bind()
        event.listen(connection, "before_cursor_execute", capture)
        try:
            response = client.patch(
                f"/api/v1/access-profiles/{profile['id']}",
                headers=administrator,
                json={**proposal(permissions=["loadx.products.read"]), "version": 1},
            )
        finally:
            event.remove(connection, "before_cursor_execute", capture)
    assert response.status_code == 200
    assert len(statements) == 1
    assert [
        client.get("/api/v1/auth/me", headers=member_headers).status_code
        for member_headers in headers
    ] == [401, 401, 401]
