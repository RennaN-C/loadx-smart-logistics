import uuid
from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.drivers.document_schemas import DocumentCreate, PolicyUpdate
from app.modules.drivers.document_service import DocumentService
from app.modules.drivers.models import (
    CNH_TYPE_ID,
    Driver,
    DriverDocument,
    DriverDocumentPolicy,
)
from app.modules.drivers.service import DriverService
from app.modules.status_history.models import AuditEvent
from app.modules.status_history.service import AuditService
from tests.integration.test_deliveries_api import seed_operational_scenario
from tests.integration.test_drivers_api import make_driver_payload
from tests.integration.test_load_planning_api import create_authenticated_user


@pytest.fixture
def manager(session_factory):
    return create_authenticated_user(session_factory, "LOGISTICS_MANAGER")


@pytest.fixture
def driver(client, manager):
    response = client.post(
        "/api/v1/drivers", headers=manager.headers, json=make_driver_payload()
    )
    assert response.status_code == 201, response.text
    return response.json()


def path(driver):
    return f"/api/v1/drivers/{driver['id']}/documents"


def payload(**change):
    now = datetime.now(UTC)
    return {
        "document_type_id": str(CNH_TYPE_ID),
        "reference": "12345678900",
        "category": "D",
        "issued_at": (now - timedelta(days=10)).isoformat(),
        "expires_at": (now + timedelta(days=60)).isoformat(),
        **change,
    }


def current(client, manager, driver):
    return next(
        row
        for row in client.get(path(driver), headers=manager.headers).json()["items"]
        if row["superseded_at"] is None and row["document_type_id"] == str(CNH_TYPE_ID)
    )


def renew(client, manager, driver, **change):
    old = current(client, manager, driver)
    response = client.post(
        f"{path(driver)}/{old['id']}/renew",
        headers=manager.headers,
        json=payload(**change),
    )
    assert response.status_code == 201, response.text
    return response.json()


def require(client, manager, driver, required=True, categories=None, type_id=None):
    response = client.patch(
        f"/api/v1/drivers/{driver['id']}/document-policies/{type_id or CNH_TYPE_ID}",
        headers=manager.headers,
        json={"required": required, "allowed_categories": categories or []},
    )
    assert response.status_code == 200, response.text
    return response.json()


def availability(client, manager, driver):
    rows = client.get(
        "/api/v1/drivers/operational-status", headers=manager.headers
    ).json()["items"]
    return next(row for row in rows if row["id"] == driver["id"])


@pytest.mark.parametrize(
    "days,status,blocked",
    [(-1, "EXPIRED", True), (1, "EXPIRING", False), (60, "VALID", False)],
)
def test_license_dates_and_explicit_policy(
    client, manager, driver, days, status, blocked
):
    record = renew(
        client,
        manager,
        driver,
        expires_at=(datetime.now(UTC) + timedelta(days=days)).isoformat(),
    )
    assert record["status"] == status
    assert availability(client, manager, driver)["available"] is True
    require(client, manager, driver)
    assert availability(client, manager, driver)["has_document_conflict"] is blocked
    assert availability(client, manager, driver)["available"] is not blocked


def test_unknown_expiry_category_and_exact_policy(client, manager, driver):
    require(client, manager, driver)
    assert availability(client, manager, driver)["has_document_conflict"] is True
    renew(client, manager, driver, category="C")
    require(client, manager, driver, categories=["D"])
    assert availability(client, manager, driver)["has_document_conflict"] is True
    require(client, manager, driver, categories=["C"])
    assert availability(client, manager, driver)["available"] is True
    renew(client, manager, driver, category=None)
    assert availability(client, manager, driver)["has_document_conflict"] is True
    require(client, manager, driver, required=False)
    assert availability(client, manager, driver)["available"] is True


def test_renewal_projection_patch_history_and_atomic_audit(
    client, session_factory, manager, driver
):
    old = current(client, manager, driver)
    new = renew(client, manager, driver, reference="98765432109", category="E")
    detail = client.get(
        f"/api/v1/drivers/{driver['id']}", headers=manager.headers
    ).json()
    assert detail["license_number"] == "98765432109"
    assert detail["license_category"] == "E"
    assert detail["license_expires_at"] == new["expires_at"]
    response = client.patch(
        f"/api/v1/drivers/{driver['id']}",
        headers=manager.headers,
        json={"license_category": "D"},
    )
    assert response.status_code == 200, response.text
    rows = client.get(path(driver), headers=manager.headers).json()["items"]
    assert len(rows) == 3
    assert sum(row["superseded_at"] is None for row in rows) == 1
    assert (
        next(row for row in rows if row["id"] == old["id"])["reference"]
        == old["reference"]
    )
    assert current(client, manager, driver)["category"] == "D"
    with session_factory() as db:
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.entity_id == uuid.UUID(new["id"]))
        ).all()
        assert {row.event_type for row in events} == {
            "DRIVER_DOCUMENT_CREATED",
            "DRIVER_DOCUMENT_RENEWED",
        }


def test_additional_type_approval_documents_and_policy(client, manager, driver):
    kind = client.post(
        "/api/v1/driver-document-types",
        headers=manager.headers,
        json={"code": "LOCAL_APPROVED", "name": "Documento aprovado local"},
    )
    assert kind.status_code == 201, kind.text
    type_id = kind.json()["id"]
    assert (
        client.post(
            "/api/v1/driver-document-types",
            headers=manager.headers,
            json={"code": "LOCAL_APPROVED", "name": "Duplicado"},
        ).status_code
        == 409
    )
    require(client, manager, driver, type_id=type_id)
    assert availability(client, manager, driver)["available"] is False
    response = client.post(
        path(driver),
        headers=manager.headers,
        json={"document_type_id": type_id, "reference": "REF-FICTICIA"},
    )
    assert response.status_code == 201, response.text
    assert availability(client, manager, driver)["available"] is True
    assert (
        client.get(path(driver) + "?page_size=1", headers=manager.headers).json()[
            "total"
        ]
        == 2
    )
    invalid = client.patch(
        f"/api/v1/drivers/{driver['id']}/document-policies/{type_id}",
        headers=manager.headers,
        json={"required": True, "allowed_categories": ["D"]},
    )
    assert invalid.status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        {"category": "XYZ"},
        {"reference": "invalid"},
        {"expires_at": None},
        {"issued_at": "2026-01-01T00:00:00"},
        {"expires_at": "2000-01-01T00:00:00Z"},
        {"file_reference": "/private/storage"},
    ],
)
def test_license_validation(client, manager, driver, change):
    old = current(client, manager, driver)
    response = client.post(
        f"{path(driver)}/{old['id']}/renew",
        headers=manager.headers,
        json=payload(**change),
    )
    assert response.status_code == 422, response.text
    assert current(client, manager, driver)["id"] == old["id"]


@pytest.mark.parametrize(
    "role,read,write",
    [
        ("ADMIN", 200, 201),
        ("LOGISTICS_MANAGER", 200, 201),
        ("CHECKER", 403, 403),
        ("DRIVER", 403, 403),
    ],
)
def test_rbac(client, session_factory, manager, driver, role, read, write):
    actor = create_authenticated_user(session_factory, role)
    old = current(client, manager, driver)
    response = client.post(
        f"{path(driver)}/{old['id']}/renew", headers=actor.headers, json=payload()
    )
    assert response.status_code == write, response.text
    assert client.get(path(driver), headers=actor.headers).status_code == read
    assert (
        client.get("/api/v1/driver-document-types", headers=actor.headers).status_code
        == read
    )
    assert (
        client.post(
            "/api/v1/driver-document-types",
            headers=actor.headers,
            json={"code": "TEST", "name": "Fictício"},
        ).status_code
        == write
    )
    assert client.patch(
        f"/api/v1/drivers/{driver['id']}/document-policies/{CNH_TYPE_ID}",
        headers=actor.headers,
        json={"required": True},
    ).status_code == (200 if write == 201 else 403)
    assert client.get(path(driver)).status_code == 401


def test_scoped_identity_duplicates_and_archived_history(client, manager, driver):
    old = current(client, manager, driver)
    assert (
        client.post(path(driver), headers=manager.headers, json=payload()).status_code
        == 409
    )
    assert (
        client.post(
            f"{path(driver)}/{uuid.uuid4()}/renew",
            headers=manager.headers,
            json=payload(),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/drivers/{uuid.uuid4()}/documents", headers=manager.headers
        ).status_code
        == 404
    )
    renew(client, manager, driver)
    assert (
        client.post(
            f"{path(driver)}/{old['id']}/renew", headers=manager.headers, json=payload()
        ).status_code
        == 409
    )
    client.patch(
        f"/api/v1/drivers/{driver['id']}",
        headers=manager.headers,
        json={"active": False},
    )
    assert client.get(path(driver), headers=manager.headers).json()["total"] == 2
    assert (
        client.post(
            f"{path(driver)}/{current(client, manager, driver)['id']}/renew",
            headers=manager.headers,
            json=payload(),
        ).status_code
        == 409
    )


def test_license_uniqueness_rolls_back_renewal(client, manager, driver):
    other = client.post(
        "/api/v1/drivers",
        headers=manager.headers,
        json=make_driver_payload("98765432100", "98765432109"),
    )
    assert other.status_code == 201
    old = current(client, manager, driver)
    result = client.post(
        f"{path(driver)}/{old['id']}/renew",
        headers=manager.headers,
        json=payload(reference="98765432109"),
    )
    assert result.status_code == 409, result.text
    assert result.json()["code"] == "DRIVER_LICENSE_NUMBER_ALREADY_EXISTS"
    assert current(client, manager, driver)["id"] == old["id"]


@pytest.mark.parametrize("operation", ["renewal", "policy", "patch"])
def test_audit_failure_rolls_back(
    client, session_factory, manager, driver, monkeypatch, operation
):
    old = current(client, manager, driver)

    def fail(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditService, "stage_administrative_event", fail)
    identifier = uuid.UUID(driver["id"])
    with session_factory() as db:
        service = DocumentService(db)
        with pytest.raises(RuntimeError, match="audit unavailable"):
            if operation == "renewal":
                service.create(
                    identifier,
                    DocumentCreate.model_validate(payload(reference="98765432109")),
                    actor=manager.id,
                    replacing=uuid.UUID(old["id"]),
                )
            elif operation == "policy":
                service.update_policy(
                    identifier,
                    CNH_TYPE_ID,
                    PolicyUpdate(required=True),
                    actor=manager.id,
                )
            else:
                from app.modules.drivers.schemas import DriverUpdate

                DriverService(db).update_driver(
                    identifier,
                    DriverUpdate(license_category="E"),
                    changed_by=manager.id,
                )
        assert db.get(Driver, identifier).license_number == old["reference"]
        assert db.get(Driver, identifier).license_category == old["category"]
        assert db.get(DriverDocument, uuid.UUID(old["id"])).superseded_at is None
        assert (
            db.scalars(
                select(DriverDocumentPolicy).where(
                    DriverDocumentPolicy.driver_id == identifier
                )
            ).all()
            == []
        )


def test_expired_license_blocks_trip_creation(client, session_factory):
    scenario = seed_operational_scenario(session_factory)
    headers = scenario.manager_headers
    identifier = str(scenario.driver_id)
    policy = client.patch(
        f"/api/v1/drivers/{identifier}/document-policies/{CNH_TYPE_ID}",
        headers=headers,
        json={"required": True},
    )
    assert policy.status_code == 200
    record = client.post(
        f"/api/v1/drivers/{identifier}/documents",
        headers=headers,
        json=payload(expires_at=(datetime.now(UTC) - timedelta(days=1)).isoformat()),
    )
    assert record.status_code == 201, record.text
    trip = client.post(
        "/api/v1/trips",
        headers=headers,
        json={"load_plan_id": str(scenario.load_plan_id), "driver_id": identifier},
    )
    assert trip.status_code == 409, trip.text
    assert trip.json()["code"] == "DRIVER_DOCUMENT_INELIGIBLE"
    record = client.post(
        f"/api/v1/drivers/{identifier}/documents/{record.json()['id']}/renew",
        headers=headers,
        json=payload(),
    )
    assert record.status_code == 201, record.text
    trip = client.post(
        "/api/v1/trips",
        headers=headers,
        json={"load_plan_id": str(scenario.load_plan_id), "driver_id": identifier},
    )
    assert trip.status_code == 201, trip.text
    assert (
        client.get(f"/api/v1/trips/{trip.json()['id']}", headers=headers).status_code
        == 200
    )


def test_constraints_and_downgrade_guard(session_factory, driver):
    with session_factory() as db:
        db.add(
            DriverDocument(
                driver_id=uuid.UUID(driver["id"]),
                document_type_id=CNH_TYPE_ID,
                reference="duplicate",
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
        migration = import_module("migrations.versions.20261009_0020_driver_documents")
        with pytest.raises(RuntimeError, match="OC102 downgrade blocked"):
            migration.ensure_safe_downgrade(db.connection())
        db.rollback()


def test_concurrent_renewal_has_one_winner(postgres_engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete
    from sqlalchemy.orm import sessionmaker

    from app.core.exceptions import ApiError
    from app.modules.drivers.schemas import DriverCreate

    factory = sessionmaker(postgres_engine, autoflush=False)
    with factory() as db:
        driver = DriverService(db).create_driver(
            DriverCreate.model_validate(make_driver_payload())
        )
        identifier = driver.id
        old = db.scalar(
            select(DriverDocument).where(
                DriverDocument.driver_id == identifier,
                DriverDocument.superseded_at.is_(None),
            )
        )
        old_id = old.id
    monkeypatch.setattr(
        AuditService, "stage_administrative_event", lambda *args, **kwargs: None
    )
    barrier = Barrier(2)
    data = DocumentCreate.model_validate(payload())

    def submit():
        with factory() as db:
            barrier.wait(timeout=10)
            try:
                DocumentService(db).create(
                    identifier, data, actor=uuid.uuid4(), replacing=old_id
                )
                return "RENEWED"
            except ApiError as error:
                return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(submit), executor.submit(submit)]
            assert {future.result(timeout=15) for future in futures} == {
                "RENEWED",
                "DRIVER_DOCUMENT_NOT_CURRENT",
            }
        with factory() as db:
            docs = db.scalars(
                select(DriverDocument).where(DriverDocument.driver_id == identifier)
            ).all()
            assert len(docs) == 2
            assert sum(row.superseded_at is None for row in docs) == 1
    finally:
        with factory() as db:
            db.execute(
                delete(DriverDocument).where(DriverDocument.driver_id == identifier)
            )
            db.execute(delete(Driver).where(Driver.id == identifier))
            db.commit()


def test_expiration_at_trip_start_preserves_historical_trip(client, session_factory):
    from app.modules.deliveries.models import Trip

    scenario = seed_operational_scenario(session_factory)
    headers = scenario.manager_headers
    identifier = str(scenario.driver_id)
    doc = client.post(
        f"/api/v1/drivers/{identifier}/documents", headers=headers, json=payload()
    ).json()
    client.patch(
        f"/api/v1/drivers/{identifier}/document-policies/{CNH_TYPE_ID}",
        headers=headers,
        json={"required": True},
    )
    trip = client.post(
        "/api/v1/trips",
        headers=headers,
        json={"load_plan_id": str(scenario.load_plan_id), "driver_id": identifier},
    )
    assert trip.status_code == 201, trip.text
    with session_factory() as db:
        record = db.get(DriverDocument, uuid.UUID(doc["id"]))
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    response = client.patch(
        f"/api/v1/trips/{trip.json()['id']}/status",
        headers=headers,
        json={"status": "IN_ROUTE"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "DRIVER_DOCUMENT_INELIGIBLE"
    with session_factory() as db:
        persisted = db.get(Trip, uuid.UUID(trip.json()["id"]))
        assert persisted.status == "SCHEDULED"
        assert persisted.driver_id == scenario.driver_id
