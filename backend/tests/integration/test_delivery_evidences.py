import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.integrations.evidence_storage import EvidenceStorageError, FakeEvidenceStorage
from app.main import app
from app.modules.auth.models import AuthSession
from app.modules.deliveries.evidence_models import DeliveryEvidence
from app.modules.deliveries.evidence_router import get_evidence_storage
from app.modules.deliveries.evidence_schemas import DeliveryEvidenceCreate
from app.modules.deliveries.evidence_service import DeliveryEvidenceService
from app.modules.deliveries.models import Delivery
from app.modules.deliveries.service import TripService
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.test_external_commands import (
    scenario as command_scenario,  # noqa: F401
)
from tests.unit.test_evidence_storage import image_base64


@pytest.fixture
def evidence_scenario(command_scenario):  # noqa: F811 - imported reusable pytest fixture
    scenario = command_scenario
    storage = FakeEvidenceStorage()
    with scenario.factory() as db:
        user = db.get(User, scenario.actors["manager"])
        TripService(db).change_delivery_status(
            scenario.delivery_id, "DELIVERED", current_user=user
        )

    def override_db():
        with scenario.factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_evidence_storage] = lambda: storage
    scenario.storage = storage
    scenario.path = f"/api/v1/deliveries/{scenario.delivery_id}/evidences"
    scenario.headers = lambda actor="manager": issue_session_headers(
        scenario.factory, scenario.actors[actor]
    )
    with TestClient(
        app, raise_server_exceptions=False, headers={"Origin": "http://localhost:5173"}
    ) as client:
        scenario.client = client
        try:
            yield scenario
        finally:
            app.dependency_overrides.clear()
            with scenario.factory() as db:
                db.execute(
                    delete(DeliveryEvidence).where(
                        DeliveryEvidence.recorded_by.in_(scenario.actors.values())
                    )
                )
                db.execute(
                    delete(AuthSession).where(
                        AuthSession.user_id.in_(scenario.actors.values())
                    )
                )
                db.commit()


def payload(**updates):
    data = {
        "event_id": str(uuid.uuid4()),
        "kind": "PHOTO",
        "content_base64": image_base64(),
    }
    data.update(updates)
    return data


def register(scenario, data=None, actor="manager"):
    return scenario.client.post(
        scenario.path, json=data or payload(), headers=scenario.headers(actor)
    )


def evidence_count(scenario):
    with scenario.factory() as db:
        return db.scalar(
            select(func.count())
            .select_from(DeliveryEvidence)
            .where(DeliveryEvidence.recorded_by.in_(scenario.actors.values()))
        )


@pytest.mark.parametrize("actor,kind", (("manager", "PHOTO"), ("driver", "SIGNATURE")))
def test_registration_replay_and_queries_preserve_receipt_and_responsible(
    evidence_scenario, actor, kind
):
    s = evidence_scenario
    data = payload(kind=kind)
    headers = s.headers(actor)
    receipt_before = s.client.get(
        s.path.removesuffix("/evidences") + "/receipt", headers=headers
    ).json()
    created = register(s, data, actor)
    assert created.status_code == 200, created.text
    evidence = created.json()
    repeated = register(s, data, actor)
    assert repeated.status_code == 200 and repeated.json() == evidence
    assert evidence["recorded_by"] == str(s.actors[actor])
    assert evidence["receipt_id"] == receipt_before["id"]
    assert evidence["delivery_id"] == str(s.delivery_id)
    assert evidence["status"] == "ACTIVE"
    assert evidence_count(s) == len(s.storage.objects) == 1
    listing = s.client.get(s.path, headers=s.headers("admin")).json()
    assert listing["items"] == [evidence] and listing["total"] == 1
    response = s.client.get(f"{s.path}/{evidence['id']}", headers=headers)
    assert response.json() == evidence
    download = s.client.get(f"{s.path}/{evidence['id']}/content", headers=headers)
    assert download.status_code == 200
    assert download.headers["content-type"] == "image/png"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert (
        s.client.get(
            s.path.removesuffix("/evidences") + "/receipt", headers=headers
        ).json()
        == receipt_before
    )
    assert (
        not {"content_base64", "storage_path", "url", "event_id", "fingerprint"}
        & evidence.keys()
    )


@pytest.mark.parametrize("actor", ("checker", "unlinked", "other_driver", "inactive"))
def test_registration_rejects_unauthorized_actor(evidence_scenario, actor):
    s = evidence_scenario
    response = register(s, actor=actor)
    assert response.status_code == 403
    assert evidence_count(s) == 0 and not s.storage.objects


def test_admin_can_register_and_revoke_delivery_evidence(evidence_scenario):
    s = evidence_scenario
    created = register(s, actor="admin")
    assert created.status_code == 200
    evidence = created.json()
    assert evidence["recorded_by"] == str(s.actors["admin"])
    revoked = s.client.post(
        f"{s.path}/{evidence['id']}/revoke", json={}, headers=s.headers("admin")
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"


def test_anonymous_csrf_and_cross_delivery_access_are_denied(evidence_scenario):
    s = evidence_scenario
    assert s.client.post(s.path, json=payload()).status_code == 401
    headers = s.headers()
    headers.pop("X-CSRF-Token")
    assert s.client.post(s.path, json=payload(), headers=headers).status_code == 403
    evidence = register(s).json()
    own = s.headers()
    assert s.client.get(f"{s.path}/{uuid.uuid4()}", headers=own).status_code == 404
    unknown_path = f"/api/v1/deliveries/{uuid.uuid4()}/evidences"
    response = s.client.post(unknown_path, json=payload(), headers=own)
    assert (
        response.status_code == 404 and response.json()["code"] == "DELIVERY_NOT_FOUND"
    )
    with s.factory() as db:
        other_delivery = db.scalar(
            select(Delivery).where(
                Delivery.trip_id == s.trip_id, Delivery.id != s.delivery_id
            )
        )
        manager = db.get(User, s.actors["manager"])
        TripService(db).change_delivery_status(
            other_delivery.id, "IN_DELIVERY", current_user=manager
        )
        TripService(db).change_delivery_status(
            other_delivery.id, "DELIVERED", current_user=manager
        )
        other_id = other_delivery.id
    wrong = f"/api/v1/deliveries/{other_id}/evidences/{evidence['id']}"
    for suffix in ("", "/content"):
        assert s.client.get(wrong + suffix, headers=own).status_code == 404
    assert s.client.post(wrong + "/revoke", json={}, headers=own).status_code == 404
    assert (
        s.client.get(
            f"{s.path}/{evidence['id']}/content", headers=s.headers("other_driver")
        ).status_code
        == 403
    )


@pytest.mark.parametrize("state", ("PENDING", "IN_DELIVERY"))
def test_non_completed_delivery_cannot_receive_evidence(evidence_scenario, state):
    s = evidence_scenario
    with s.factory() as db:
        delivery = db.get(Delivery, s.delivery_id)
        delivery.status = state
        delivery.delivered_at = None
        db.commit()
    response = register(s)
    assert (
        response.status_code == 409
        and response.json()["code"] == "DELIVERY_RECEIPT_NOT_AVAILABLE"
    )
    assert evidence_count(s) == 0 and not s.storage.objects


@pytest.mark.parametrize(
    "extra",
    (
        {"user_id": str(uuid.uuid4())},
        {"role": "ADMIN"},
        {"delivery_id": str(uuid.uuid4())},
        {"url": "https://invalid.test/file"},
        {"filename": "../../file"},
        {"mime_type": "image/png"},
    ),
)
def test_client_controlled_identity_or_storage_fields_are_rejected(
    evidence_scenario, extra
):
    assert register(evidence_scenario, payload(**extra)).status_code == 422
    assert evidence_count(evidence_scenario) == 0


@pytest.mark.parametrize(
    "updates",
    (
        {"kind": "PDF"},
        {"content_base64": "invalid"},
        {"content_base64": "PGh0bWw+"},
        {"event_id": "invalid"},
    ),
)
def test_invalid_type_content_and_event_identity_are_rejected(
    evidence_scenario, updates
):
    assert register(evidence_scenario, payload(**updates)).status_code == 422
    assert not evidence_scenario.storage.objects


def test_event_identity_conflict_and_revocation_replay_preserve_history(
    evidence_scenario,
):
    s = evidence_scenario
    data = payload()
    created = register(s, data).json()
    for changed in (
        dict(data, kind="SIGNATURE"),
        dict(data, content_base64=image_base64(color="blue")),
    ):
        response = register(s, changed)
        assert (
            response.status_code == 409
            and response.json()["code"] == "EVIDENCE_IDENTITY_CONFLICT"
        )
    path = f"{s.path}/{created['id']}"
    revoke = s.client.post(path + "/revoke", json={}, headers=s.headers("driver"))
    assert revoke.status_code == 200
    metadata = revoke.json()
    assert metadata["status"] == "REVOKED" and metadata["revoked_by"] == str(
        s.actors["driver"]
    )
    assert metadata["recorded_by"] == created["recorded_by"]
    assert (
        s.client.post(path + "/revoke", json={}, headers=s.headers()).json() == metadata
    )
    assert s.client.get(path, headers=s.headers("admin")).json() == metadata
    download = s.client.get(path + "/content", headers=s.headers())
    assert download.status_code == 409 and download.json()["code"] == "EVIDENCE_REVOKED"
    assert register(s, data).json() == metadata
    assert evidence_count(s) == len(s.storage.objects) == 1
    assert (
        s.client.post(path + "/revoke", json={}, headers=s.headers("admin")).json()
        == metadata
    )


def test_adapter_partial_failure_is_compensated_without_sensitive_logs(
    evidence_scenario, monkeypatch, caplog
):
    s = evidence_scenario
    original = s.storage.put

    def failing(key, content):
        original(key, content)
        raise EvidenceStorageError

    monkeypatch.setattr(s.storage, "put", failing)
    with caplog.at_level(logging.INFO):
        response = register(s)
    assert response.status_code == 503
    assert evidence_count(s) == 0 and not s.storage.objects
    assert "content_base64" not in caplog.text


def test_commit_failure_compensates_blob_and_metadata(evidence_scenario, monkeypatch):
    s = evidence_scenario
    with s.factory() as db:
        user = db.get(User, s.actors["manager"])
        service = DeliveryEvidenceService(db, s.storage)
        with monkeypatch.context() as patcher:
            patcher.setattr(
                db,
                "commit",
                lambda: (_ for _ in ()).throw(RuntimeError("fixture-failure")),
            )
            with pytest.raises(RuntimeError):
                service.register(
                    s.delivery_id,
                    DeliveryEvidenceCreate(**payload()),
                    current_user=user,
                )
    assert evidence_count(s) == 0 and not s.storage.objects
    assert register(s).status_code == 200


def test_uncertain_commit_does_not_delete_bytes_referenced_by_committed_row(
    evidence_scenario, monkeypatch
):
    s = evidence_scenario
    data = payload()
    with s.factory() as db:
        user = db.get(User, s.actors["manager"])
        commit = db.commit

        def commit_then_fail():
            commit()
            raise RuntimeError("fixture-connection-interrupted-after-commit")

        with monkeypatch.context() as patcher:
            patcher.setattr(db, "commit", commit_then_fail)
            with pytest.raises(RuntimeError):
                DeliveryEvidenceService(db, s.storage).register(
                    s.delivery_id, DeliveryEvidenceCreate(**data), current_user=user
                )
    assert evidence_count(s) == len(s.storage.objects) == 1
    response = register(s, data)
    assert response.status_code == 200
    assert (
        s.client.get(
            f"{s.path}/{response.json()['id']}/content", headers=s.headers()
        ).status_code
        == 200
    )


def test_compensation_failure_logs_only_opaque_identity_and_never_exposes_orphan(
    evidence_scenario, monkeypatch, caplog
):
    s = evidence_scenario
    original_put = s.storage.put

    def failing_put(key, data):
        original_put(key, data)
        raise EvidenceStorageError

    def failing_discard(_key):
        raise RuntimeError("private-provider-token-and-path")

    monkeypatch.setattr(s.storage, "put", failing_put)
    monkeypatch.setattr(s.storage, "discard", failing_discard)
    with caplog.at_level(logging.ERROR, logger="loadx.security"):
        response = register(s)
    assert response.status_code == 503 and evidence_count(s) == 0
    assert len(s.storage.objects) == 1
    log = next(
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "loadx.security"
        and "DELIVERY_EVIDENCE_CLEANUP_FAILED" in record.getMessage()
    )
    assert set(log) == {"alert", "event", "occurred_at", "evidence_id"}
    assert "private-provider-token" not in caplog.text + response.text
    orphan_id = next(iter(s.storage.objects))
    assert (
        s.client.get(f"{s.path}/{orphan_id}/content", headers=s.headers()).status_code
        == 404
    )


def test_storage_registration_rejects_savepoint_as_commit_boundary(evidence_scenario):
    s = evidence_scenario
    with s.factory() as outer, outer.begin():  # noqa: SIM117 - explicit outer/savepoint ownership
        with Session(
            bind=outer.connection(), join_transaction_mode="create_savepoint"
        ) as inner:
            user = inner.get(User, s.actors["manager"])
            with pytest.raises(EvidenceStorageError):
                DeliveryEvidenceService(inner, s.storage).register(
                    s.delivery_id,
                    DeliveryEvidenceCreate(**payload()),
                    current_user=user,
                )
    assert evidence_count(s) == 0 and not s.storage.objects


def test_revocation_rollback_preserves_active_content(evidence_scenario, monkeypatch):
    s = evidence_scenario
    created = register(s).json()
    with s.factory() as db:
        user = db.get(User, s.actors["manager"])
        service = DeliveryEvidenceService(db, s.storage)
        with monkeypatch.context() as patcher:
            patcher.setattr(
                db,
                "commit",
                lambda: (_ for _ in ()).throw(RuntimeError("fixture-failure")),
            )
            with pytest.raises(RuntimeError):
                service.revoke(
                    s.delivery_id, uuid.UUID(created["id"]), current_user=user
                )
    assert (
        s.client.get(
            f"{s.path}/{created['id']}/content", headers=s.headers()
        ).status_code
        == 200
    )
    assert (
        s.client.get(f"{s.path}/{created['id']}", headers=s.headers()).json()["status"]
        == "ACTIVE"
    )


def test_missing_or_tampered_blob_fails_closed(evidence_scenario):
    s = evidence_scenario
    created = register(s).json()
    key = uuid.UUID(created["id"])
    s.storage.objects[key] = b"tampered"
    path = f"{s.path}/{key}/content"
    assert s.client.get(path, headers=s.headers()).status_code == 503
    s.storage.discard(key)
    assert s.client.get(path, headers=s.headers()).status_code == 503


def test_concurrent_replay_serializes_and_writes_one_blob(evidence_scenario):
    s = evidence_scenario
    data = DeliveryEvidenceCreate(**payload())
    barrier = Barrier(2)

    def execute():
        with s.factory() as db:
            user = db.get(User, s.actors["manager"])
            barrier.wait(timeout=5)
            return DeliveryEvidenceService(db, s.storage).register(
                s.delivery_id, data, current_user=user
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            future.result(timeout=15)
            for future in [executor.submit(execute) for _ in range(2)]
        ]
    assert results[0] == results[1]
    assert evidence_count(s) == len(s.storage.objects) == 1


def test_database_unique_constraint_does_not_depend_on_memory(evidence_scenario):
    s = evidence_scenario
    created = register(s).json()
    with s.factory() as db:
        row = db.get(DeliveryEvidence, uuid.UUID(created["id"]))
        values = {
            column.name: getattr(row, column.name)
            for column in DeliveryEvidence.__table__.columns
            if column.name != "id"
        }
        db.add(DeliveryEvidence(**values))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    assert evidence_count(s) == 1


def test_openapi_contract_is_additive_and_excludes_client_identity():
    schema = app.openapi()
    create = schema["components"]["schemas"]["DeliveryEvidenceCreate"]
    assert set(create["properties"]) == {"event_id", "kind", "content_base64"}
    assert create["additionalProperties"] is False
    paths = schema["paths"]
    assert "/api/v1/deliveries/{delivery_id}/receipt" in paths
    assert "/api/v1/deliveries/{delivery_id}/evidences/{evidence_id}/revoke" in paths
    binary = paths["/api/v1/deliveries/{delivery_id}/evidences/{evidence_id}/content"][
        "get"
    ]["responses"]["200"]["content"]
    assert set(binary) == {"image/png", "image/jpeg"}
