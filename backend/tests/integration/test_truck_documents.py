import uuid
from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from app.modules.trucks.document_schemas import DocumentCreate
from app.modules.trucks.document_service import DocumentService
from app.modules.trucks.models import TruckDocument, TruckDocumentPolicy
from app.modules.trucks.service import TruckService
from tests.integration.test_load_planning_api import (
    create_authenticated_user,
    seed_planning_scenario,
)
from tests.integration.test_trucks_api import make_truck_payload


@pytest.fixture
def manager(session_factory):
    return create_authenticated_user(session_factory, "LOGISTICS_MANAGER")


@pytest.fixture
def truck(client, manager):
    response = client.post(
        "/api/v1/trucks", headers=manager.headers, json=make_truck_payload()
    )
    assert response.status_code == 201
    return response.json()


def path(truck):
    return f"/api/v1/trucks/{truck['id']}/documents"


def payload(**change):
    now = datetime.now(UTC)
    return {
        "kind": "CRLV",
        "reference": "REF-FICTICIA",
        "issued_at": (now - timedelta(days=1)).isoformat(),
        "expires_at": (now + timedelta(days=60)).isoformat(),
        **change,
    }


def create(client, manager, truck, **change):
    result = client.post(path(truck), headers=manager.headers, json=payload(**change))
    assert result.status_code == 201, result.text
    return result.json()


def require(client, manager, truck, kind="CRLV", required=True):
    response = client.patch(
        f"/api/v1/trucks/{truck['id']}/document-policies/{kind}",
        headers=manager.headers,
        json={"required": required},
    )
    assert response.status_code == 200, response.text
    return response.json()


def availability(client, manager, truck):
    records = client.get(
        "/api/v1/trucks/operational-status", headers=manager.headers
    ).json()["items"]
    return next(row for row in records if row["id"] == truck["id"])


@pytest.mark.parametrize("kind", ["CRLV", "LICENSING", "INSURANCE"])
def test_current_document_policy_and_renewal_history(
    client, session_factory, manager, truck, kind
):
    assert availability(client, manager, truck)["available"] is True
    require(client, manager, truck, kind)
    assert availability(client, manager, truck)["has_document_conflict"] is True
    old = create(client, manager, truck, kind=kind, file_reference=str(uuid.uuid4()))
    assert old["status"] == "VALID"
    assert availability(client, manager, truck)["available"] is True
    duplicate = client.post(
        path(truck), headers=manager.headers, json=payload(kind=kind)
    )
    assert duplicate.status_code == 409
    renewed = client.post(
        f"{path(truck)}/{old['id']}/renew",
        headers=manager.headers,
        json=payload(kind=kind, reference="NOVO"),
    )
    assert renewed.status_code == 201, renewed.text
    rows = client.get(path(truck), headers=manager.headers).json()["items"]
    assert len(rows) == 2
    previous = next(row for row in rows if row["id"] == old["id"])
    assert previous["status"] == "SUPERSEDED"
    assert previous["file_reference"] == old["file_reference"]
    assert previous["reference"] == old["reference"]
    assert sum(row["superseded_at"] is None for row in rows) == 1
    assert (
        client.post(
            f"{path(truck)}/{old['id']}/renew",
            headers=manager.headers,
            json=payload(kind=kind, reference="OUTRO"),
        ).status_code
        == 409
    )
    with session_factory() as db:
        events = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == uuid.UUID(old["id"]))
            .order_by(AuditEvent.created_at)
        ).all()
        assert [row.event_type for row in events] == [
            "TRUCK_DOCUMENT_CREATED",
            "TRUCK_DOCUMENT_RENEWED",
        ]


@pytest.mark.parametrize(
    "issued,expires,status,blocked",
    [
        (-10, -1, "EXPIRED", True),
        (-10, 1, "EXPIRING", False),
        (-10, 60, "VALID", False),
        (1, 60, "NOT_YET_VALID", True),
        (None, None, "VALID", False),
    ],
)
def test_status_and_explicit_policy(
    client, manager, truck, issued, expires, status, blocked
):
    now = datetime.now(UTC)
    record = create(
        client,
        manager,
        truck,
        issued_at=(now + timedelta(days=issued)).isoformat()
        if issued is not None
        else None,
        expires_at=(now + timedelta(days=expires)).isoformat()
        if expires is not None
        else None,
    )
    assert record["status"] == status
    assert availability(client, manager, truck)["available"] is True
    require(client, manager, truck)
    assert availability(client, manager, truck)["has_document_conflict"] is blocked
    require(client, manager, truck, required=False)
    assert availability(client, manager, truck)["available"] is True


def test_exact_validity_boundaries(client, session_factory, manager, truck):
    now = datetime.now(UTC)
    create(
        client,
        manager,
        truck,
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    require(client, manager, truck)
    with session_factory() as db:
        service = TruckService(db)
        identifier = uuid.UUID(truck["id"])
        assert service.has_document_conflict(
            identifier, at=now - timedelta(microseconds=1)
        )
        assert not service.has_document_conflict(identifier, at=now)
        assert service.has_document_conflict(identifier, at=now + timedelta(days=30))


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "UNKNOWN"},
        {"reference": " "},
        {"expires_at": "2000-01-01T00:00:00Z"},
        {"issued_at": "2026-01-01T00:00:00"},
        {"file_reference": "/private/storage/file"},
        {"file_reference": "https://private.example/file"},
        {"extra": "value"},
    ],
)
def test_document_validation(client, manager, truck, change):
    assert (
        client.post(
            path(truck), headers=manager.headers, json=payload(**change)
        ).status_code
        == 422
    )
    assert client.get(path(truck), headers=manager.headers).json()["total"] == 0


@pytest.mark.parametrize(
    "role,read,write",
    [
        ("ADMIN", 200, 201),
        ("LOGISTICS_MANAGER", 200, 201),
        ("CHECKER", 200, 403),
        ("DRIVER", 403, 403),
    ],
)
def test_document_rbac(client, session_factory, manager, truck, role, read, write):
    actor = create_authenticated_user(session_factory, role)
    assert (
        client.post(path(truck), headers=actor.headers, json=payload()).status_code
        == write
    )
    assert client.get(path(truck), headers=actor.headers).status_code == read
    assert (
        client.get(
            f"/api/v1/trucks/{truck['id']}/document-policies", headers=actor.headers
        ).status_code
        == read
    )
    assert client.patch(
        f"/api/v1/trucks/{truck['id']}/document-policies/CRLV",
        headers=actor.headers,
        json={"required": True},
    ).status_code == (200 if write == 201 else 403)
    records = client.get(path(truck), headers=manager.headers).json()["items"]
    old = records[0] if records else create(client, manager, truck)
    assert (
        client.post(
            f"{path(truck)}/{old['id']}/renew",
            headers=actor.headers,
            json=payload(reference="RENOVADO"),
        ).status_code
        == write
    )
    assert client.get(path(truck)).status_code == 401


def test_scoping_pagination_archive_and_policy_idempotency(
    client, session_factory, manager, truck
):
    old = create(client, manager, truck)
    policy = require(client, manager, truck)
    require(client, manager, truck)
    with session_factory() as db:
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.entity_id == uuid.UUID(policy["id"]))
        ).all()
        assert len(events) == 1
    assert (
        client.post(
            f"{path(truck)}/{uuid.uuid4()}/renew",
            headers=manager.headers,
            json=payload(),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/trucks/{uuid.uuid4()}/documents", headers=manager.headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"{path(truck)}/{old['id']}/renew",
            headers=manager.headers,
            json={key: old[key] for key in DocumentCreate.model_fields},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{path(truck)}/{old['id']}/renew",
            headers=manager.headers,
            json=payload(kind="INSURANCE"),
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/trucks/{truck['id']}/document-policies/UNKNOWN",
            headers=manager.headers,
            json={"required": True},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/trucks/{truck['id']}/document-policies/CRLV",
            headers=manager.headers,
            json={"required": "true"},
        ).status_code
        == 422
    )
    assert (
        client.get(path(truck) + "?page_size=1", headers=manager.headers).json()[
            "page_size"
        ]
        == 1
    )
    client.patch(
        f"/api/v1/trucks/{truck['id']}", headers=manager.headers, json={"active": False}
    )
    assert client.get(path(truck), headers=manager.headers).json()["total"] == 1
    assert (
        client.post(
            path(truck), headers=manager.headers, json=payload(kind="INSURANCE")
        ).status_code
        == 409
    )
    assert availability(client, manager, truck)["active"] is False


@pytest.mark.parametrize(
    "operation", ["plan", "approval", "loading", "trip", "distribution"]
)
def test_policy_blocks_new_operations_preserving_plans(
    client, session_factory, manager, operation
):
    scenario = seed_planning_scenario(session_factory)
    truck = {"id": str(scenario.truck_id)}
    plan_payload = {"truck_id": truck["id"], "order_ids": [str(scenario.order_id)]}
    plan = client.post(
        "/api/v1/load-plans", headers=manager.headers, json=plan_payload
    ).json()
    if operation in ("loading", "trip"):
        assert (
            client.post(
                f"/api/v1/load-plans/{plan['id']}/approve",
                headers=manager.headers,
                json={},
            ).status_code
            == 200
        )
    require(client, manager, truck)
    if operation == "plan":
        response = client.post(
            "/api/v1/load-plans", headers=manager.headers, json=plan_payload
        )
    elif operation == "approval":
        response = client.post(
            f"/api/v1/load-plans/{plan['id']}/approve", headers=manager.headers, json={}
        )
    elif operation == "loading":
        response = client.post(
            "/api/v1/loading-sessions",
            headers=manager.headers,
            json={"load_plan_id": plan["id"]},
        )
    elif operation == "trip":
        from tests.integration.test_drivers_api import make_driver_payload

        driver = client.post(
            "/api/v1/drivers", headers=manager.headers, json=make_driver_payload()
        ).json()
        response = client.post(
            "/api/v1/trips",
            headers=manager.headers,
            json={"load_plan_id": plan["id"], "driver_id": driver["id"]},
        )
    else:
        response = client.post(
            "/api/v1/load-distributions/preflight",
            headers=manager.headers,
            json={"order_ids": [str(scenario.order_id)]},
        )
        assert response.status_code == 200, response.text
        assert response.json()["eligible_trucks"] == []
        assert (
            response.json()["ineligible_trucks"][0]["reason"]
            == "TRUCK_DOCUMENT_INELIGIBLE"
        )
        return
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "TRUCK_DOCUMENT_INELIGIBLE"
    assert (
        client.get(
            f"/api/v1/load-plans/{plan['id']}", headers=manager.headers
        ).status_code
        == 200
    )


def test_renewal_failure_rolls_back_history(
    client, session_factory, manager, truck, monkeypatch
):
    old = create(client, manager, truck)

    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
    with session_factory() as db:
        with pytest.raises(RuntimeError, match="audit unavailable"):
            DocumentService(db).create(
                uuid.UUID(truck["id"]),
                DocumentCreate.model_validate(payload(reference="NEW")),
                actor=manager.id,
                replacing=uuid.UUID(old["id"]),
            )
        persisted = db.get(TruckDocument, uuid.UUID(old["id"]))
        assert persisted.superseded_at is None
        assert (
            len(
                db.scalars(
                    select(TruckDocument).where(
                        TruckDocument.truck_id == uuid.UUID(truck["id"])
                    )
                ).all()
            )
            == 1
        )


def test_database_constraints_and_downgrade_guard(
    client, session_factory, manager, truck
):
    create(client, manager, truck)
    with session_factory() as db:
        db.add(
            TruckDocument(
                truck_id=uuid.UUID(truck["id"]), kind="CRLV", reference="DUPLICATE"
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
        migration = import_module("migrations.versions.20261009_0019_truck_documents")
        with pytest.raises(RuntimeError, match="OC101 downgrade blocked"):
            migration.ensure_safe_downgrade(db.connection())
        db.rollback()
        db.add(
            TruckDocumentPolicy(
                truck_id=uuid.UUID(truck["id"]), kind="UNKNOWN", required=True
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_concurrent_document_creation_has_one_current_version(
    postgres_engine, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import sessionmaker

    from app.core.exceptions import ApiError
    from app.modules.trucks.models import Truck
    from app.modules.trucks.schemas import TruckCreate

    factory = sessionmaker(postgres_engine, autoflush=False)
    with factory() as db:
        truck = TruckService(db).create_truck(
            TruckCreate.model_validate(make_truck_payload())
        )
        identifier = truck.id
    monkeypatch.setattr(DocumentService, "stage_audit", lambda *args, **kwargs: None)
    barrier = Barrier(2)

    def submit():
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                DocumentService(db).create(
                    identifier,
                    DocumentCreate.model_validate(payload()),
                    actor=uuid.uuid4(),
                )
                return "CREATED"
            except ApiError as error:
                return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(submit), executor.submit(submit)]
            assert {future.result(timeout=15) for future in futures} == {
                "CREATED",
                "TRUCK_DOCUMENT_DUPLICATE",
            }
        with factory() as db:
            assert (
                len(
                    db.scalars(
                        select(TruckDocument).where(
                            TruckDocument.truck_id == identifier
                        )
                    ).all()
                )
                == 1
            )
    finally:
        with factory() as db:
            db.execute(
                delete(TruckDocument).where(TruckDocument.truck_id == identifier)
            )
            db.execute(delete(Truck).where(Truck.id == identifier))
            db.commit()


def test_policy_audit_failure_rolls_back(session_factory, manager, truck, monkeypatch):
    from app.modules.trucks.document_schemas import PolicyUpdate

    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
    with session_factory() as db:
        with pytest.raises(RuntimeError, match="audit unavailable"):
            DocumentService(db).update_policy(
                uuid.UUID(truck["id"]),
                "CRLV",
                PolicyUpdate(required=True),
                actor=manager.id,
            )
        assert (
            db.scalars(
                select(TruckDocumentPolicy).where(
                    TruckDocumentPolicy.truck_id == uuid.UUID(truck["id"])
                )
            ).all()
            == []
        )
        assert not TruckService(db).has_document_conflict(uuid.UUID(truck["id"]))


def test_expiration_blocks_starting_existing_loading(client, session_factory, manager):
    scenario = seed_planning_scenario(session_factory)
    truck = {"id": str(scenario.truck_id)}
    old = create(client, manager, truck, issued_at="2020-01-01T00:00:00Z")
    require(client, manager, truck)
    plan = client.post(
        "/api/v1/load-plans",
        headers=manager.headers,
        json={"truck_id": truck["id"], "order_ids": [str(scenario.order_id)]},
    ).json()
    assert (
        client.post(
            f"/api/v1/load-plans/{plan['id']}/approve", headers=manager.headers, json={}
        ).status_code
        == 200
    )
    loading = client.post(
        "/api/v1/loading-sessions",
        headers=manager.headers,
        json={"load_plan_id": plan["id"]},
    )
    assert loading.status_code == 201, loading.text
    with session_factory() as db:
        record = db.get(TruckDocument, uuid.UUID(old["id"]))
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    checker = create_authenticated_user(session_factory, "CHECKER")
    response = client.patch(
        f"/api/v1/loading-sessions/{loading.json()['id']}/status",
        headers=checker.headers,
        json={"status": "IN_PROGRESS"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "TRUCK_DOCUMENT_INELIGIBLE"
    create_response = client.post(
        f"{path(truck)}/{old['id']}/renew", headers=manager.headers, json=payload()
    )
    assert create_response.status_code == 201, create_response.text
    response = client.patch(
        f"/api/v1/loading-sessions/{loading.json()['id']}/status",
        headers=checker.headers,
        json={"status": "IN_PROGRESS"},
    )
    assert response.status_code == 200, response.text
