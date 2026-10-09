import base64
import uuid
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.database.session import get_db
from app.integrations.evidence_storage import EvidenceStorageError, FakeEvidenceStorage
from app.main import app
from app.modules.attachments.models import OperationalAttachment
from app.modules.attachments.router import get_attachment_storage
from app.modules.attachments.schemas import AttachmentCreate
from app.modules.attachments.service import AttachmentService
from app.modules.auth.models import AuthSession
from app.modules.deliveries.models import Delivery
from app.modules.occurrences.models import Occurrence
from app.modules.status_history.models import AuditEvent
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_external_commands import (
    scenario as command_scenario,  # noqa: F401
)
from tests.unit.test_evidence_storage import image_base64


@pytest.fixture
def attachments(command_scenario):  # noqa: F811
    s = command_scenario
    s.storage = FakeEvidenceStorage()
    with s.factory() as db:
        s.order_id = db.get(Delivery, s.delivery_id).order_id
        occurrence = Occurrence(
            trip_id=s.trip_id, type="OTHER", description="Fixture fictícia"
        )
        db.add(occurrence)
        db.flush()
        s.occurrence_id = occurrence.id
        db.commit()
    s.resources = {
        "orders": s.order_id,
        "trips": s.trip_id,
        "deliveries": s.delivery_id,
        "occurrences": s.occurrence_id,
    }
    s.path = lambda resource="deliveries": (
        f"/api/v1/attachments/{resource}/{s.resources[resource]}"
    )
    s.headers = lambda actor="manager": issue_session_headers(
        s.factory, s.actors[actor]
    )

    def override_db():
        with s.factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_attachment_storage] = lambda: s.storage
    with TestClient(
        app, headers={"Origin": "http://localhost:5173"}, raise_server_exceptions=False
    ) as client:
        s.client = client
        try:
            yield s
        finally:
            app.dependency_overrides.clear()
            with s.factory() as db:
                db.execute(
                    delete(AuditEvent).where(AuditEvent.actor_id.in_(s.actors.values()))
                )
                db.execute(
                    delete(OperationalAttachment).where(
                        OperationalAttachment.recorded_by.in_(s.actors.values())
                    )
                )
                db.execute(delete(Occurrence).where(Occurrence.id == s.occurrence_id))
                db.execute(
                    delete(AuthSession).where(
                        AuthSession.user_id.in_(s.actors.values())
                    )
                )
                db.commit()


def payload(**updates):
    return {"event_id": str(uuid.uuid4()), "content_base64": image_base64(), **updates}


def create(s, resource="deliveries", actor="manager", data=None):
    return s.client.post(
        s.path(resource), json=data or payload(), headers=s.headers(actor)
    )


@pytest.mark.parametrize("resource", ["orders", "trips", "deliveries", "occurrences"])
@pytest.mark.parametrize("actor", ["admin", "manager"])
def test_register_download_replay_revoke_and_audit(attachments, resource, actor):
    s = attachments
    data = payload()
    created = create(s, resource, actor, data)
    assert created.status_code == 200, created.text
    row = created.json()
    assert row["resource_id"] == str(s.resources[resource])
    assert row["resource_type"] == resource and row["recorded_by"] == str(
        s.actors[actor]
    )
    assert row["status"] == "ACTIVE"
    assert not {"content_base64", "event_id", "fingerprint", "url", "path"} & row.keys()
    assert create(s, resource, actor, data).json() == row
    assert len(s.storage.objects) == 1
    path = f"{s.path(resource)}/{row['id']}"
    assert s.client.get(path, headers=s.headers(actor)).json() == row
    assert s.client.get(s.path(resource), headers=s.headers(actor)).json()["items"] == [
        row
    ]
    downloaded = s.client.get(path + "/content", headers=s.headers(actor))
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "image/png"
    assert downloaded.headers["cache-control"] == "no-store"
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert downloaded.headers["content-disposition"].startswith("attachment;")
    removed = s.client.post(path + "/revoke", json={}, headers=s.headers(actor))
    assert removed.status_code == 200 and removed.json()["status"] == "REVOKED"
    assert removed.json()["revoked_by"] == str(s.actors[actor])
    assert (
        s.client.post(path + "/revoke", json={}, headers=s.headers(actor)).json()
        == removed.json()
    )
    assert s.client.get(path + "/content", headers=s.headers(actor)).status_code == 409
    assert create(s, resource, actor, data).json() == removed.json()
    assert len(s.storage.objects) == 1
    with s.factory() as db:
        events = db.scalars(
            select(AuditEvent.event_type).where(
                AuditEvent.entity_id == uuid.UUID(row["id"])
            )
        ).all()
        assert sorted(events) == ["ATTACHMENT_REGISTERED", "ATTACHMENT_REVOKED"]
        assert db.get(Delivery, s.delivery_id).status == "IN_DELIVERY"


@pytest.mark.parametrize("resource", ["trips", "deliveries", "occurrences"])
def test_linked_driver_and_wrong_driver(attachments, resource):
    s = attachments
    assert create(s, resource, "driver").status_code == 200
    for actor in ("checker", "other_driver", "unlinked"):
        assert create(s, resource, actor).status_code == 403
        assert (
            s.client.get(s.path(resource), headers=s.headers(actor)).status_code == 403
        )


def test_order_checker_read_only_driver_denied(attachments):
    s = attachments
    row = create(s, "orders").json()
    assert (
        s.client.get(s.path("orders"), headers=s.headers("checker")).status_code == 200
    )
    assert create(s, "orders", "checker").status_code == 403
    assert create(s, "orders", "driver").status_code == 403
    assert (
        s.client.get(s.path("orders"), headers=s.headers("driver")).status_code == 403
    )
    assert (
        s.client.post(
            f"{s.path('orders')}/{row['id']}/revoke",
            json={},
            headers=s.headers("checker"),
        ).status_code
        == 403
    )


@pytest.mark.parametrize("resource", ["orders", "trips", "deliveries", "occurrences"])
def test_unknown_resource_and_cross_context(attachments, resource):
    s = attachments
    path = f"/api/v1/attachments/{resource}/{uuid.uuid4()}"
    assert s.client.post(path, json=payload(), headers=s.headers()).status_code == 404
    assert s.client.get(path, headers=s.headers()).status_code == 404
    row = create(s).json()
    assert (
        s.client.get(f"{s.path('trips')}/{row['id']}", headers=s.headers()).status_code
        == 404
    )
    assert (
        s.client.get(f"{s.path()}/{uuid.uuid4()}", headers=s.headers()).status_code
        == 404
    )


@pytest.mark.parametrize(
    "source",
    [
        "not base64",
        base64.b64encode(b"<html>bad</html>").decode(),
        base64.b64encode(b"%PDF-1.7 invalid").decode(),
        base64.b64encode(b"x" * (5242880 + 1)).decode(),
    ],
)
def test_invalid_content_rejected_before_storage(attachments, source):
    s = attachments
    assert create(s, data=payload(content_base64=source)).status_code == 422
    assert not s.storage.objects


def test_identity_conflict_and_client_metadata_rejected(attachments):
    s = attachments
    data = payload()
    assert create(s, data=data).status_code == 200
    assert create(s, "trips", data=data).status_code == 409
    assert (
        create(
            s, data={**data, "content_base64": image_base64(color="blue")}
        ).status_code
        == 409
    )
    for field in ("recorded_by", "media_type", "url", "resource_id"):
        assert create(s, data=payload(**{field: "malicious"})).status_code == 422
    assert len(s.storage.objects) == 1


def test_anonymous_csrf_inactive_and_removed_driver(attachments):
    s = attachments
    assert s.client.post(s.path(), json=payload()).status_code == 401
    headers = s.headers()
    headers.pop("X-CSRF-Token")
    assert s.client.post(s.path(), json=payload(), headers=headers).status_code == 403
    assert create(s, actor="inactive").status_code == 403
    from app.modules.drivers.models import Driver

    with s.factory() as db:
        db.get(Driver, s.driver_id).active = False
        db.commit()
    assert create(s, actor="driver").status_code == 403
    assert not s.storage.objects


def test_failed_storage_and_audit_rollback(attachments, monkeypatch):
    s = attachments
    original = s.storage.put

    def fail(key, content):
        original(key, content)
        raise EvidenceStorageError

    monkeypatch.setattr(s.storage, "put", fail)
    assert create(s).status_code == 503
    assert not s.storage.objects
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OperationalAttachment)) == 0
    monkeypatch.setattr(s.storage, "put", original)

    def audit_failure(*args):
        raise RuntimeError("fixture")

    monkeypatch.setattr(AttachmentService, "_audit", audit_failure)
    assert create(s).status_code == 500
    assert not s.storage.objects
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OperationalAttachment)) == 0


def test_corrupt_missing_blob_and_metadata_without_storage(attachments):
    s = attachments
    row = create(s).json()
    path = f"{s.path()}/{row['id']}"
    s.storage.objects[uuid.UUID(row["id"])] = b"corrupt"
    assert s.client.get(path + "/content", headers=s.headers()).status_code == 503
    s.storage.objects.clear()
    assert s.client.get(path + "/content", headers=s.headers()).status_code == 503
    app.dependency_overrides.pop(get_attachment_storage)
    assert s.client.get(s.path(), headers=s.headers()).status_code == 200
    assert (
        s.client.post(path + "/revoke", json={}, headers=s.headers()).status_code == 200
    )


def test_concurrent_retries_have_one_blob_and_one_audit(attachments):
    s = attachments
    barrier = Barrier(2)
    data = AttachmentCreate(**payload())

    def register():
        with s.factory() as db:
            user = db.get(User, s.actors["manager"])
            barrier.wait(timeout=10)
            return (
                AttachmentService(db, s.storage)
                .register("trips", s.trip_id, data, current_user=user)
                .id
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: register(), range(2)))
    assert results[0] == results[1] and len(s.storage.objects) == 1
    with s.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.entity_id == results[0])
            )
            == 1
        )


@pytest.mark.parametrize(
    "mutation",
    [
        {"trip_id": None},
        {"order_id": "extra"},
        {"size_bytes": 0},
        {"media_type": "text/html"},
        {"status": "REVOKED"},
        {"trip_id": "unknown"},
    ],
)
def test_database_constraints_protect_outside_service(attachments, mutation):
    s = attachments
    values = {
        "id": uuid.uuid4(),
        "trip_id": s.trip_id,
        "recorded_by": s.actors["manager"],
        "event_id": uuid.uuid4(),
        "media_type": "image/png",
        "size_bytes": 5,
        "sha256": "a" * 64,
        "fingerprint": "b" * 64,
    }
    values.update(
        {
            k: (s.order_id if v == "extra" else uuid.uuid4() if v == "unknown" else v)
            for k, v in mutation.items()
        }
    )
    with s.factory() as db:
        db.add(OperationalAttachment(**values))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_downgrade_refuses_historical_attachments(attachments):
    s = attachments
    row = create(s).json()
    s.client.post(f"{s.path()}/{row['id']}/revoke", json={}, headers=s.headers())
    migration = import_module(
        "migrations.versions.20261009_0021_operational_attachments"
    )
    with s.factory() as db:
        with pytest.raises(RuntimeError, match="history and audit"):
            migration.ensure_safe_downgrade(db.connection())
        with pytest.raises(IntegrityError):
            db.execute(delete(Delivery).where(Delivery.id == s.delivery_id))
        db.rollback()


def test_upload_refuses_savepoint_bound_session(attachments):
    from sqlalchemy.orm import Session

    s = attachments
    with s.factory() as outer:
        user = outer.get(User, s.actors["manager"])
        with (
            Session(bind=outer.connection()) as nested,
            pytest.raises(EvidenceStorageError),
        ):
            AttachmentService(nested, s.storage).register(
                "trips", s.trip_id, AttachmentCreate(**payload()), current_user=user
            )
    assert not s.storage.objects


def test_uncertain_commit_preserves_committed_blob_and_audit(attachments, monkeypatch):
    s = attachments
    with s.factory() as db:
        user = db.get(User, s.actors["manager"])
        original = db.commit

        def uncertain_commit():
            original()
            raise RuntimeError("fixture: lost commit acknowledgment")

        monkeypatch.setattr(db, "commit", uncertain_commit)
        with pytest.raises(RuntimeError):
            AttachmentService(db, s.storage).register(
                "trips", s.trip_id, AttachmentCreate(**payload()), current_user=user
            )
    with s.factory() as db:
        row = db.scalar(select(OperationalAttachment))
        assert row is not None and row.id in s.storage.objects
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.entity_id == row.id)
            )
            == 1
        )


def test_failed_commit_compensates_new_blob(attachments, monkeypatch):
    s = attachments
    with s.factory() as db:
        user = db.get(User, s.actors["manager"])

        def failed_commit():
            raise RuntimeError("fixture: failed commit")

        monkeypatch.setattr(db, "commit", failed_commit)
        with pytest.raises(RuntimeError):
            AttachmentService(db, s.storage).register(
                "trips", s.trip_id, AttachmentCreate(**payload()), current_user=user
            )
    assert not s.storage.objects


def test_download_and_revoke_serialize_on_attachment_row(attachments, monkeypatch):
    from concurrent.futures import TimeoutError as FutureTimeout
    from threading import Event

    s = attachments
    key = uuid.UUID(create(s, "trips").json()["id"])
    reading, release, revoking = Event(), Event(), Event()
    original = s.storage.read

    def slow_read(object_id):
        reading.set()
        assert release.wait(timeout=10)
        return original(object_id)

    monkeypatch.setattr(s.storage, "read", slow_read)

    def download():
        with s.factory() as db:
            user = db.get(User, s.actors["manager"])
            return AttachmentService(db, s.storage).download(
                "trips", s.trip_id, key, current_user=user
            )

    def revoke():
        with s.factory() as db:
            user = db.get(User, s.actors["manager"])
            revoking.set()
            return AttachmentService(db).revoke(
                "trips", s.trip_id, key, current_user=user
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        downloaded = pool.submit(download)
        try:
            assert reading.wait(timeout=10)
            revoked = pool.submit(revoke)
            assert revoking.wait(timeout=10)
            with pytest.raises(FutureTimeout):
                revoked.result(timeout=0.2)
        finally:
            release.set()
        assert downloaded.result(timeout=10)[1] == "image/png"
        assert revoked.result(timeout=10).status == "REVOKED"
    assert key in s.storage.objects
