import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import StatusHistoryService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from tests.integration.auth_helpers import issue_session_headers

SessionFactory = Callable[[], Session]


def create_user(
    session_factory: SessionFactory,
    email: str,
    role: str,
) -> User:
    db = session_factory()
    try:
        return UserService(db).create_user(
            UserCreate(
                name=f"Usuário {role}",
                email=email,
                password="senha-local-segura",
                role=role,
                active=True,
            )
        )
    finally:
        db.close()


def headers_for(session_factory: SessionFactory, user: User) -> dict[str, str]:
    return issue_session_headers(session_factory, user.id)


def record_status(
    session_factory: SessionFactory,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    actor_id: uuid.UUID | None,
) -> None:
    db = session_factory()
    try:
        StatusHistoryService(db).record_status_change(
            StatusHistoryCreate(
                entity_type=entity_type,
                entity_id=entity_id,
                old_status=None,
                new_status="DRAFT" if entity_type == "ORDER" else "CREATED",
                changed_by=actor_id,
            )
        )
    finally:
        db.close()


@pytest.fixture
def admin(session_factory: SessionFactory) -> User:
    return create_user(session_factory, "audit-admin@example.test", "ADMIN")


@pytest.fixture
def admin_headers(
    session_factory: SessionFactory,
    admin: User,
) -> dict[str, str]:
    return headers_for(session_factory, admin)


def test_audit_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/audit")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize("role", ["CHECKER", "DRIVER"])
def test_audit_rejects_roles_without_general_history_access(
    client: TestClient,
    session_factory: SessionFactory,
    role: str,
) -> None:
    user = create_user(
        session_factory,
        f"audit-{role.lower()}@example.test",
        role,
    )

    response = client.get(
        "/api/v1/audit",
        headers=headers_for(session_factory, user),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_FORBIDDEN"


def test_logistics_manager_can_read_general_history(
    client: TestClient,
    session_factory: SessionFactory,
) -> None:
    manager = create_user(
        session_factory,
        "audit-manager@example.test",
        "LOGISTICS_MANAGER",
    )

    response = client.get(
        "/api/v1/audit",
        headers=headers_for(session_factory, manager),
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "items",
        "page",
        "page_size",
        "total",
        "total_pages",
    }


def test_audit_lists_and_filters_each_operational_entity_before_pagination(
    client: TestClient,
    session_factory: SessionFactory,
    admin: User,
    admin_headers: dict[str, str],
) -> None:
    entity_ids = {
        entity_type: uuid.uuid4()
        for entity_type in ("ORDER", "LOAD_PLAN", "TRIP", "DELIVERY")
    }
    for entity_type, entity_id in entity_ids.items():
        record_status(
            session_factory,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=admin.id,
        )

    for entity_type, entity_id in entity_ids.items():
        response = client.get(
            "/api/v1/audit",
            params={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "page": 1,
                "page_size": 1,
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["total_pages"] == 1
        assert body["items"][0]["event_type"] == "STATUS_CHANGED"
        assert body["items"][0]["entity_type"] == entity_type
        assert body["items"][0]["entity_id"] == str(entity_id)
        assert body["items"][0]["actor_id"] == str(admin.id)
        assert body["items"][0]["actor_name"] == admin.name


def test_audit_filters_by_actor_event_type_and_period(
    client: TestClient,
    session_factory: SessionFactory,
    admin: User,
    admin_headers: dict[str, str],
) -> None:
    record_status(
        session_factory,
        entity_type="ORDER",
        entity_id=uuid.uuid4(),
        actor_id=admin.id,
    )

    response = client.get(
        "/api/v1/audit",
        params={
            "actor_id": str(admin.id),
            "event_type": "STATUS_CHANGED",
            "start_at": "2026-01-01T00:00:00Z",
            "end_at": "2027-01-01T00:00:00Z",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(item["actor_id"] == str(admin.id) for item in body["items"])
    assert all(item["event_type"] == "STATUS_CHANGED" for item in body["items"])


def test_audit_paginates_after_server_side_filters(
    client: TestClient,
    session_factory: SessionFactory,
    admin: User,
    admin_headers: dict[str, str],
) -> None:
    entity_id = uuid.uuid4()
    record_status(
        session_factory,
        entity_type="ORDER",
        entity_id=entity_id,
        actor_id=admin.id,
    )
    db = session_factory()
    try:
        StatusHistoryService(db).record_status_change(
            StatusHistoryCreate(
                entity_type="ORDER",
                entity_id=entity_id,
                old_status="DRAFT",
                new_status="READY",
                changed_by=admin.id,
            )
        )
    finally:
        db.close()

    first = client.get(
        "/api/v1/audit",
        params={
            "entity_type": "ORDER",
            "entity_id": str(entity_id),
            "page": 1,
            "page_size": 1,
            "sort_order": "asc",
        },
        headers=admin_headers,
    )
    second = client.get(
        "/api/v1/audit",
        params={
            "entity_type": "ORDER",
            "entity_id": str(entity_id),
            "page": 2,
            "page_size": 1,
            "sort_order": "asc",
        },
        headers=admin_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["total"] == 2
    assert first.json()["total_pages"] == 2
    assert first.json()["items"][0]["id"] != second.json()["items"][0]["id"]


def test_admin_user_actions_are_audited_without_sensitive_values(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    password = "segredo-auditoria-2026"
    create_response = client.post(
        "/api/v1/users",
        json={
            "name": "Alvo da Auditoria",
            "email": "audit-target@example.test",
            "password": password,
            "role": "CHECKER",
        },
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/users/{user_id}",
        json={
            "name": "Alvo Atualizado",
            "password": "outra-senha-auditoria-2026",
        },
        headers=admin_headers,
    )
    assert update_response.status_code == 200

    response = client.get(
        "/api/v1/audit",
        params={"entity_type": "USER", "entity_id": user_id},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    event_types = {item["event_type"] for item in body["items"]}
    assert event_types == {"USER_CREATED", "USER_UPDATED"}

    updated = next(
        item for item in body["items"] if item["event_type"] == "USER_UPDATED"
    )
    assert updated["changed_fields"] == ["name", "password"]
    serialized = response.text
    assert password not in serialized
    assert "outra-senha-auditoria-2026" not in serialized
    assert "audit-target@example.test" not in serialized
    assert "Alvo Atualizado" not in serialized


def test_audit_rejects_invalid_period(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.get(
        "/api/v1/audit",
        params={
            "start_at": "2026-10-07T00:00:00Z",
            "end_at": "2026-10-06T00:00:00Z",
        },
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "AUDIT_INVALID_PERIOD"


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_audit_has_no_write_endpoint(
    client: TestClient,
    admin_headers: dict[str, str],
    method: str,
) -> None:
    response = client.request(
        method,
        "/api/v1/audit",
        json={"event_type": "USER_UPDATED"},
        headers=admin_headers,
    )

    assert response.status_code == 405
