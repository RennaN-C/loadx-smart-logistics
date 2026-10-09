import importlib.util
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.modules.company_profile.models import PROFILE_ID, CompanyProfile
from app.modules.company_profile.schemas import CompanyProfileInput
from app.modules.company_profile.service import CompanyProfileService
from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from app.modules.users.models import User
from tests.integration.test_users_api import authorization_headers, create_user_in_db

PAYLOAD = {
    "legal_name": "Empresa de Teste Ltda",
    "display_name": "Empresa de Teste",
    "cnpj": "11.222.333/0001-81",
    "phone": "(11) 90000-0000",
    "email": "CONTATO@EXAMPLE.TEST",
    "logo_reference": "https://example.test/logo.svg",
}


@pytest.fixture
def admin(session_factory):
    return create_user_in_db(session_factory, "oc91-admin@example.test")


@pytest.fixture
def headers(session_factory, admin):
    return authorization_headers(session_factory, admin)


def test_read_empty_does_not_create(client, headers, session_factory):
    assert client.get("/api/v1/company-profile", headers=headers).json() is None
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(CompanyProfile)) == 0


def test_save_update_persist_and_audit(client, headers, session_factory, admin):
    response = client.put("/api/v1/company-profile", headers=headers, json=PAYLOAD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(PROFILE_ID)
    assert body["cnpj"] == "11222333000181"
    assert body["phone"] == "11900000000"
    assert body["email"] == "contato@example.test"
    assert client.get("/api/v1/company-profile", headers=headers).json() == body
    assert (
        client.put("/api/v1/company-profile", headers=headers, json=PAYLOAD).status_code
        == 200
    )
    changed = {**PAYLOAD, "display_name": "Novo nome"}
    assert (
        client.put("/api/v1/company-profile", headers=headers, json=changed).status_code
        == 200
    )
    with session_factory() as db:
        assert db.get(CompanyProfile, PROFILE_ID).display_name == "Novo nome"
        events = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_type == "COMPANY_PROFILE")
            .order_by(AuditEvent.created_at)
        ).all()
        assert len(events) == 2
        assert events[0].event_type == "COMPANY_PROFILE_CREATED"
        assert events[1].changed_fields == "display_name"
        assert all(event.actor_id == admin.id for event in events)
        assert all("example.test" not in event.changed_fields for event in events)
    audit = client.get(
        "/api/v1/audit", headers=headers, params={"entity_type": "COMPANY_PROFILE"}
    )
    assert audit.status_code == 200
    assert audit.json()["total"] == 2
    assert (
        client.get(
            "/api/v1/audit",
            headers=headers,
            params={"event_type": "COMPANY_PROFILE_UPDATED"},
        ).json()["total"]
        == 1
    )


@pytest.mark.parametrize("role", ["LOGISTICS_MANAGER", "CHECKER", "DRIVER"])
@pytest.mark.parametrize("method", ["get", "put"])
def test_other_roles_cannot_read_or_write(client, session_factory, role, method):
    user = create_user_in_db(session_factory, "role@example.test", role)
    kwargs = {"headers": authorization_headers(session_factory, user)}
    if method == "put":
        kwargs["json"] = PAYLOAD
    assert (
        getattr(client, method)("/api/v1/company-profile", **kwargs).status_code == 403
    )


@pytest.mark.parametrize("method", ["get", "put"])
def test_unauthenticated(client, method):
    kwargs = {"json": PAYLOAD} if method == "put" else {}
    assert (
        getattr(client, method)("/api/v1/company-profile", **kwargs).status_code == 401
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("legal_name", " "),
        ("display_name", ""),
        ("legal_name", "x" * 161),
        ("cnpj", "11111111111111"),
        ("cnpj", "11222333000182"),
        ("cnpj", "abc"),
        ("phone", "123"),
        ("email", "invalid"),
        ("email", "a@"),
        ("logo_reference", "http://example.test/logo"),
        ("logo_reference", "javascript:alert(1)"),
        ("logo_reference", "https://user:secret@example.test/logo"),
        ("logo_reference", "https://"),
        ("logo_reference", "https://example.test:999999/logo"),
        ("logo_reference", "https://example.test/a b"),
        ("logo_reference", "https://example.test:0/logo"),
        ("logo_reference", "data:image/png;base64,AA"),
        ("tenant_id", str(uuid.uuid4())),
        ("secret", "do-not-store"),
    ],
)
def test_invalid_data_does_not_persist(client, headers, session_factory, field, value):
    response = client.put(
        "/api/v1/company-profile", headers=headers, json={**PAYLOAD, field: value}
    )
    assert response.status_code == 422, response.text
    assert any(detail["field"] == field for detail in response.json()["details"])
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(CompanyProfile)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.entity_type == "COMPANY_PROFILE")
            )
            == 0
        )


def test_optional_fields_can_be_cleared(client, headers):
    assert (
        client.put("/api/v1/company-profile", headers=headers, json=PAYLOAD).status_code
        == 200
    )
    response = client.put(
        "/api/v1/company-profile",
        headers=headers,
        json={
            "legal_name": " Nome ",
            "display_name": " Exibição ",
            "cnpj": " ",
            "phone": "",
            "email": " ",
            "logo_reference": None,
        },
    )
    assert response.status_code == 200
    assert response.json()["legal_name"] == "Nome"
    assert all(
        response.json()[key] is None
        for key in ("cnpj", "phone", "email", "logo_reference")
    )


def test_manager_cannot_discover_company_audit(client, headers, session_factory):
    client.put("/api/v1/company-profile", headers=headers, json=PAYLOAD)
    manager = create_user_in_db(
        session_factory, "manager@example.test", "LOGISTICS_MANAGER"
    )
    manager_headers = authorization_headers(session_factory, manager)
    result = client.get("/api/v1/audit", headers=manager_headers)
    assert result.status_code == 200
    assert all(
        row["entity_type"] != "COMPANY_PROFILE" for row in result.json()["items"]
    )
    for params in [
        {"entity_type": "COMPANY_PROFILE"},
        {"event_type": "COMPANY_PROFILE_CREATED"},
        {"event_type": "COMPANY_PROFILE_UPDATED"},
    ]:
        assert (
            client.get(
                "/api/v1/audit", headers=manager_headers, params=params
            ).status_code
            == 403
        )


@pytest.mark.parametrize("existing", [False, True])
def test_audit_failure_rolls_back_entire_operation(
    session_factory, admin, monkeypatch, existing
):
    with session_factory() as db:
        service = CompanyProfileService(db)
        if existing:
            service.update(CompanyProfileInput(**PAYLOAD), admin.id)

        def fail(_self, _data):
            raise RuntimeError("simulated audit failure")

        monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
        with pytest.raises(RuntimeError):
            service.update(
                CompanyProfileInput(**{**PAYLOAD, "display_name": "Must rollback"}),
                admin.id,
            )
    with session_factory() as db:
        profile = db.get(CompanyProfile, PROFILE_ID)
        assert (profile.display_name if profile else None) == (
            PAYLOAD["display_name"] if existing else None
        )
        assert db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.entity_type == "COMPANY_PROFILE")
        ) == int(existing)


def test_concurrent_first_save_preserves_singleton(postgres_engine):
    factory = sessionmaker(bind=postgres_engine, autoflush=False)
    admin = create_user_in_db(factory, "concurrent-oc91@example.test")

    def save(name):
        with factory() as db:
            return (
                CompanyProfileService(db)
                .update(
                    CompanyProfileInput(**{**PAYLOAD, "display_name": name}), admin.id
                )
                .id
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert list(executor.map(save, ["Primeiro", "Segundo"])) == [
                PROFILE_ID,
                PROFILE_ID,
            ]
        with factory() as db:
            assert db.scalar(select(func.count()).select_from(CompanyProfile)) == 1
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.entity_type == "COMPANY_PROFILE")
                )
                == 2
            )
    finally:
        with factory() as db:
            db.execute(delete(AuditEvent).where(AuditEvent.actor_id == admin.id))
            db.execute(delete(CompanyProfile))
            db.execute(delete(User).where(User.id == admin.id))
            db.commit()


@pytest.mark.parametrize(
    "values",
    [
        {"id": uuid.uuid4(), "legal_name": "A", "display_name": "B"},
        {"id": PROFILE_ID, "legal_name": " ", "display_name": "B"},
        {"id": PROFILE_ID, "legal_name": "A", "display_name": "B", "cnpj": "bad"},
    ],
)
def test_database_constraints(session_factory, values):
    with session_factory() as db:
        db.add(CompanyProfile(**values))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_downgrade_preserves_institutional_record(session_factory, admin):
    path = (
        Path(__file__).resolve().parents[2]
        / "migrations/versions/20261009_0023_company_profile.py"
    )
    spec = importlib.util.spec_from_file_location("oc91_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with session_factory() as db:
        migration.ensure_safe_downgrade(db.connection())
        CompanyProfileService(db).update(CompanyProfileInput(**PAYLOAD), admin.id)
        with pytest.raises(RuntimeError, match="must be preserved"):
            migration.ensure_safe_downgrade(db.connection())
        db.execute(text("DELETE FROM company_profiles"))
        with pytest.raises(RuntimeError, match="must be preserved"):
            migration.ensure_safe_downgrade(db.connection())
        db.rollback()


def test_openapi_contract(client):
    schema = client.get("/openapi.json").json()
    path = schema["paths"]["/api/v1/company-profile"]
    for method in ["get", "put"]:
        assert all(
            str(code) in path[method]["responses"] for code in [200, 401, 403, 422]
        )
    properties = schema["components"]["schemas"]["CompanyProfileInput"]["properties"]
    assert set(properties) == set(PAYLOAD)
