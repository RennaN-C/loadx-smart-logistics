"""OC109 PostgreSQL 16: independent workers, transactions and personal inbox."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import Mock

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import ApiError
from app.integrations.outbox import PermanentDeliveryError, TransientDeliveryError
from app.modules.auth.models import AuthSession
from app.modules.notifications.models import (
    NotificationRecipient,
    OperationalNotification,
)
from app.modules.notifications.outbox_models import (
    OutboxAttempt,
    OutboxEvent,
    OutboxRetryCommand,
)
from app.modules.notifications.outbox_repository import OutboxRepository
from app.modules.notifications.outbox_service import OutboxService
from app.modules.notifications.worker import process_one
from app.modules.status_history.models import AuditEvent
from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers
from tests.integration.notification_helpers import clear_outbox_fixture
from tests.integration.test_durable_notifications import register, row_for
from tests.integration.test_external_commands import scenario

__all__ = ("scenario",)
BASE = "/api/v1/outbox-events"


@pytest.fixture
def session_factory(postgres_engine):
    # Real API commits must not hold locks inside the suite's savepoint fixture.
    return sessionmaker(bind=postgres_engine, autoflush=False)


@pytest.fixture
def queued(scenario):
    s = scenario
    with s.factory() as db:
        clear_outbox_fixture(db, s.trip_id)
        db.commit()
    occurrence = register(s)
    with s.factory() as db:
        identifier = db.scalar(select(OutboxEvent.id))
    yield s, identifier, row_for(s, occurrence).id
    with s.factory() as db:
        db.execute(
            delete(AuthSession).where(AuthSession.user_id.in_(s.actors.values()))
        )
        db.commit()


def snapshot(s, identifier):
    with s.factory() as db:
        row = db.get(OutboxEvent, identifier)
        return row.status, row.attempt_count, row.generation, row.last_error_code


def due(s, identifier):
    with s.factory() as db:
        row = db.get(OutboxEvent, identifier)
        row.next_attempt_at = OutboxRepository(db).now() - timedelta(seconds=1)
        db.commit()


def retry(s, identifier, command=None):
    with s.factory() as db:
        return OutboxService(db).retry(
            identifier, command or uuid.uuid4(), db.get(User, s.actors["admin"])
        )


def test_success_is_durable_and_keeps_internal_receipts(queued):
    s, identifier, notification = queued
    with s.factory() as db:
        recipients = list(
            db.scalars(
                select(NotificationRecipient.user_id).where(
                    NotificationRecipient.notification_id == notification
                )
            )
        )
    transport = Mock()
    assert process_one(s.factory, transport)
    assert snapshot(s, identifier) == ("SUCCEEDED", 1, 1, None)
    assert not process_one(s.factory, transport)
    assert transport.send.call_count == 1
    with s.factory() as db:
        assert db.get(OperationalNotification, notification).mock_status == "SIMULATED"
        assert (
            list(
                db.scalars(
                    select(NotificationRecipient.user_id).where(
                        NotificationRecipient.notification_id == notification
                    )
                )
            )
            == recipients
        )
        assert db.scalar(select(OutboxAttempt)).result == "SUCCEEDED"


@pytest.mark.parametrize(
    "error,status,code",
    [
        (TransientDeliveryError("secret"), "RETRYABLE", "TRANSIENT"),
        (PermanentDeliveryError("secret"), "TERMINAL", "PERMANENT"),
        (TimeoutError("secret"), "UNCERTAIN", "TIMEOUT_UNKNOWN"),
        (RuntimeError("secret"), "UNCERTAIN", "UNKNOWN_RESULT"),
    ],
)
def test_transport_failure_is_sanitized_and_scheduled(queued, error, status, code):
    s, identifier, _ = queued
    transport = Mock()
    transport.send.side_effect = error
    process_one(s.factory, transport)
    assert snapshot(s, identifier) == (status, 1, 1, code)
    assert not process_one(s.factory, transport)
    with s.factory() as db:
        row = db.get(OutboxEvent, identifier)
        if status == "RETRYABLE":
            assert 14 <= (row.next_attempt_at - row.updated_at).total_seconds() <= 31
        assert db.scalar(select(OutboxAttempt)).error_code == code


def test_retry_exhaustion_and_manual_reprocessing_preserve_history(queued):
    s, identifier, notification = queued
    transport = Mock()
    transport.send.side_effect = TransientDeliveryError()
    process_one(s.factory, transport, max_attempts=2)
    due(s, identifier)
    process_one(s.factory, transport, max_attempts=2)
    assert snapshot(s, identifier) == ("TERMINAL", 2, 2, "EXHAUSTED")
    command = uuid.uuid4()
    retry(s, identifier, command)
    transport.send.side_effect = None
    process_one(s.factory, transport)
    assert snapshot(s, identifier) == ("SUCCEEDED", 1, 3, None)
    # Retry of the administrative HTTP command after worker success is a no-op.
    retry(s, identifier, command)
    assert snapshot(s, identifier) == ("SUCCEEDED", 1, 3, None)
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OutboxAttempt)) == 3
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.event_type == "OUTBOX_REPROCESSED")
            )
            == 1
        )
        assert db.get(OperationalNotification, notification).mock_status == "FAILED"


def test_two_workers_claim_one_event_and_transport_runs_outside_transaction(queued):
    s, identifier, _ = queued
    barrier = Barrier(2)
    calls = []

    class Transport:
        def send(self, envelope):
            with s.factory() as observer:
                row = observer.get(OutboxEvent, identifier)
                assert row.status == "PROCESSING"
                assert observer.scalar(select(OutboxAttempt)).result == "PROCESSING"
            calls.append(envelope.idempotency_key)

    def worker(_):
        barrier.wait(timeout=10)
        return process_one(s.factory, Transport())

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(worker, range(2))) == [False, True]
    assert len(calls) == 1


def test_expired_lease_restart_and_stale_result_are_fenced(queued):
    s, identifier, _ = queued
    with s.factory() as db, db.begin():
        old = OutboxService(db).claim(60)
    # Simulate the persisted clock boundary after a crash, no sleep or volatile queue.
    with s.factory() as db, db.begin():
        row = db.get(OutboxEvent, identifier)
        row.lease_expires_at = OutboxRepository(db).now() - timedelta(seconds=1)
    transport = Mock()
    assert not process_one(s.factory, transport)
    transport.send.assert_not_called()
    assert snapshot(s, identifier)[0:1] == ("UNCERTAIN",)
    retry(s, identifier)
    with s.factory() as db, db.begin():
        current = OutboxService(db).claim(60)
    with s.factory() as db, db.begin():
        assert not OutboxService(db).complete(
            old, "SUCCEEDED", None, max_attempts=5, base_seconds=30, cap_seconds=3600
        )
    with s.factory() as db, db.begin():
        assert OutboxService(db).complete(
            current,
            "SUCCEEDED",
            None,
            max_attempts=5,
            base_seconds=30,
            cap_seconds=3600,
        )
    assert snapshot(s, identifier)[:3] == ("SUCCEEDED", 1, 2)


def test_expired_result_is_uncertain_even_before_recovery_worker(queued):
    s, identifier, _ = queued
    with s.factory() as db, db.begin():
        claim = OutboxService(db).claim(60)
    with s.factory() as db, db.begin():
        db.get(OutboxEvent, identifier).lease_expires_at = OutboxRepository(
            db
        ).now() - timedelta(seconds=1)
    with s.factory() as db, db.begin():
        assert not OutboxService(db).complete(
            claim, "SUCCEEDED", None, max_attempts=5, base_seconds=30, cap_seconds=3600
        )
    assert snapshot(s, identifier)[0] == "UNCERTAIN"


def test_duplicate_stage_and_rollback_keep_exactly_one_domain_fact(queued, monkeypatch):
    s, _identifier, notification = queued
    with s.factory() as db, db.begin():
        row = db.get(OperationalNotification, notification)
        for _ in range(2):
            OutboxService(db).stage(row)
        assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 1

    def fail(self, notification):
        raise RuntimeError("fixture")

    monkeypatch.setattr(OutboxService, "stage", fail)
    with pytest.raises(RuntimeError):
        register(s)
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(OperationalNotification)
                .where(OperationalNotification.event_type == "OCCURRENCE_REGISTERED")
            )
            == 1
        )


@pytest.mark.parametrize(
    "legacy,target,code",
    [
        ("SIMULATED", "SUCCEEDED", None),
        ("FAILED", "TERMINAL", "LEGACY_FAILED"),
        ("ATTEMPT_CLAIMED", "UNCERTAIN", "LEGACY_UNKNOWN"),
        ("NO_RECIPIENT", "SUCCEEDED", "NO_RECIPIENT"),
    ],
)
def test_legacy_attempt_is_adopted_without_resending(queued, legacy, target, code):
    s, identifier, notification = queued
    with s.factory() as db, db.begin():
        from app.modules.notifications.repository import (
            OperationalNotificationRepository,
        )

        repo = OperationalNotificationRepository(db)
        assert repo.claim(notification)
        if legacy != "ATTEMPT_CLAIMED":
            repo.complete(notification, legacy)
    transport = Mock()
    assert not process_one(s.factory, transport)
    transport.send.assert_not_called()
    assert snapshot(s, identifier) == (target, 0, 0, code)
    with s.factory() as db:
        assert db.scalar(select(OutboxAttempt)).origin == "LEGACY"
        assert db.get(OperationalNotification, notification).mock_status == legacy


def test_missing_current_recipient_blocks_mock_without_losing_inbox(queued):
    s, identifier, notification = queued
    from app.modules.drivers.models import Driver

    with s.factory() as db, db.begin():
        db.get(Driver, s.driver_id).active = False
    transport = Mock()
    process_one(s.factory, transport)
    transport.send.assert_not_called()
    assert snapshot(s, identifier)[::3] == ("TERMINAL", "NO_RECIPIENT")
    with s.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(NotificationRecipient)
                .where(NotificationRecipient.notification_id == notification)
            )
            > 0
        )


@pytest.mark.parametrize(
    "role,status",
    [
        ("admin", 200),
        ("manager", 403),
        ("checker", 403),
        ("driver", 403),
        ("other_driver", 403),
        ("unlinked", 403),
    ],
)
def test_admin_api_and_non_admin_roles(client, queued, role, status):
    s, identifier, _ = queued
    headers = issue_session_headers(s.factory, s.actors[role])
    paths = [
        "",
        "/summary",
        f"/{identifier}",
        f"/{identifier}/attempts",
        f"/{identifier}/source",
    ]
    for path in paths:
        response = client.get(BASE + path, headers=headers)
        assert response.status_code == status, response.text
    result = client.post(
        f"{BASE}/{identifier}/retry",
        headers=headers,
        json={"command_id": str(uuid.uuid4())},
    )
    assert result.status_code == (409 if role == "admin" else 403)


def test_api_paging_source_sanitization_csrf_and_idempotency(client, queued):
    s, identifier, _ = queued
    assert client.get(BASE).status_code == 401
    headers = issue_session_headers(s.factory, s.actors["admin"])
    transport = Mock()
    transport.send.side_effect = PermanentDeliveryError("token=secret+phone")
    process_one(s.factory, transport)
    response = client.get(
        BASE,
        headers=headers,
        params={"status": "TERMINAL", "page_size": 1, "sort_order": "asc"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(identifier)
    assert all(
        key not in data["items"][0]
        for key in ["idempotency_key", "payload", "recipient_phone", "content"]
    )
    assert "secret" not in response.text
    assert (
        client.get(BASE, headers=headers, params={"page_size": 101}).status_code == 422
    )
    assert (
        client.get(f"{BASE}/{identifier}/source", headers=headers).json()["href"]
        == f"/trips/{s.trip_id}"
    )
    no_csrf = {"Cookie": headers["Cookie"]}
    command = {"command_id": str(uuid.uuid4())}
    assert (
        client.post(
            f"{BASE}/{identifier}/retry", headers=no_csrf, json=command
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{BASE}/{identifier}/retry", headers=headers, json=command
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{BASE}/{identifier}/retry", headers=headers, json=command
        ).status_code
        == 200
    )
    assert (
        client.get(BASE + "/summary", headers=headers).json()["counts"]["PENDING"] == 1
    )


def test_simultaneous_manual_commands_only_one_reset_and_audit(queued, monkeypatch):
    s, identifier, _ = queued
    transport = Mock()
    transport.send.side_effect = PermanentDeliveryError()
    process_one(s.factory, transport)
    barrier = Barrier(2)
    original_get = OutboxRepository.get

    def synchronized_lock(repository, identifier, *, lock=False):
        if lock:
            barrier.wait(timeout=10)
        return original_get(repository, identifier, lock=lock)

    monkeypatch.setattr(OutboxRepository, "get", synchronized_lock)

    def run(_):
        try:
            retry(s, identifier)
            return 200
        except ApiError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == [200, 409]
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OutboxRetryCommand)) == 1


def test_retry_audit_failure_rolls_back_command_and_state(queued, monkeypatch):
    s, identifier, _ = queued
    transport = Mock()
    transport.send.side_effect = PermanentDeliveryError()
    process_one(s.factory, transport)
    from app.modules.status_history.service import AuditService

    monkeypatch.setattr(
        AuditService,
        "stage_administrative_event",
        Mock(side_effect=RuntimeError("fixture")),
    )
    with pytest.raises(RuntimeError):
        retry(s, identifier)
    assert snapshot(s, identifier)[0] == "TERMINAL"
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OutboxRetryCommand)) == 0


def test_database_constraints_protect_immutable_origin_status_and_attempts(queued):
    s, identifier, _ = queued
    process_one(s.factory, Mock())
    statements = [
        update(OutboxEvent)
        .where(OutboxEvent.id == identifier)
        .values(status="PENDING"),
        update(OutboxEvent)
        .where(OutboxEvent.id == identifier)
        .values(notification_id=uuid.uuid4()),
        update(OutboxEvent)
        .where(OutboxEvent.id == identifier)
        .values(last_error_code="token=secret"),
        update(OutboxAttempt).values(result="TERMINAL"),
    ]
    for stmt in statements:
        with s.factory() as db, pytest.raises(IntegrityError):
            db.execute(stmt)


def test_populated_downgrade_refuses_history_loss(queued):
    from importlib import import_module

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    s, _, _ = queued
    module = import_module("migrations.versions.20261020_0027_outbox_events")
    with (
        s.factory() as db,
        Operations.context(MigrationContext.configure(db.connection())),
        pytest.raises(RuntimeError, match="downgrade refused"),
    ):
        module.downgrade()


@pytest.mark.parametrize(
    "legacy,target",
    [
        ("SIMULATED", "SUCCEEDED"),
        ("FAILED", "TERMINAL"),
        ("ATTEMPT_CLAIMED", "UNCERTAIN"),
        ("NO_RECIPIENT", "SUCCEEDED"),
    ],
)
def test_upgrade_backfill_preserves_oc84_and_oc103_without_sending(
    queued, legacy, target
):
    from app.modules.notifications.repository import OperationalNotificationRepository
    from tests.integration.conftest import _required_test_database_url, _run_alembic

    s, _, notification = queued
    with s.factory() as db:
        repository = OperationalNotificationRepository(db)
        repository.claim(notification)
        if legacy != "ATTEMPT_CLAIMED":
            repository.complete(notification, legacy)
        recipients = list(
            db.scalars(
                select(NotificationRecipient.user_id).where(
                    NotificationRecipient.notification_id == notification
                )
            )
        )
        clear_outbox_fixture(db)
        db.commit()
    _run_alembic(_required_test_database_url(), "downgrade", "20261020_0026")
    _run_alembic(_required_test_database_url(), "upgrade", "head")
    with s.factory() as db:
        event = db.scalar(
            select(OutboxEvent).where(OutboxEvent.notification_id == notification)
        )
        assert event.status == target
        assert event.generation == 0
        attempt = db.scalar(
            select(OutboxAttempt).where(OutboxAttempt.outbox_event_id == event.id)
        )
        assert attempt.origin == "LEGACY"
        assert db.get(OperationalNotification, notification).mock_status == legacy
        assert (
            list(
                db.scalars(
                    select(NotificationRecipient.user_id).where(
                        NotificationRecipient.notification_id == notification
                    )
                )
            )
            == recipients
        )


def test_pagination_is_deterministic_empty_pages_keep_totals(queued):
    from app.core.pagination import PaginationParams

    s, _, _ = queued
    for _ in range(3):
        register(s)
    with s.factory() as db:
        service = OutboxService(db)
        asc = service.list_events(
            PaginationParams(1, 2, "asc"), status=None, event_type=None
        )
        second = service.list_events(
            PaginationParams(2, 2, "asc"), status=None, event_type=None
        )
        desc = service.list_events(
            PaginationParams(1, 4, "desc"), status=None, event_type=None
        )
        assert asc.total == second.total == desc.total == 4
        ids = [row.id for row in asc.items + second.items]
        assert len(set(ids)) == 4
        assert ids == [row.id for row in desc.items][::-1]
        empty = service.list_events(
            PaginationParams(20, 2, "asc"), status=None, event_type=None
        )
        assert empty.items == []
        assert empty.total == 4
        assert (
            service.list_events(
                PaginationParams(1, 20, "asc"), status="TERMINAL", event_type=None
            ).total
            == 0
        )


def test_same_manual_command_concurrent_replay_has_one_audit(queued):
    s, identifier, _ = queued
    transport = Mock()
    transport.send.side_effect = PermanentDeliveryError()
    process_one(s.factory, transport)
    command, barrier = uuid.uuid4(), Barrier(2)

    def run(_):
        barrier.wait(timeout=10)
        return retry(s, identifier, command).status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(run, range(2))) == ["PENDING", "PENDING"]
    with s.factory() as db:
        assert db.scalar(select(func.count()).select_from(OutboxRetryCommand)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.event_type == "OUTBOX_REPROCESSED")
            )
            == 1
        )


def test_service_rejects_non_admin_and_command_reuse_on_other_event(queued):
    s, identifier, _ = queued
    with s.factory() as db:
        service = OutboxService(db)
        command_id = uuid.uuid4()
        actor = db.get(User, s.actors["manager"])
        with pytest.raises(ApiError) as denied:
            service.retry(identifier, command_id, actor)
        assert denied.value.status_code == 403
    transport = Mock()
    transport.send.side_effect = PermanentDeliveryError()
    process_one(s.factory, transport)
    command = uuid.uuid4()
    retry(s, identifier, command)
    other_occurrence = register(s)
    with s.factory() as db:
        notification = db.scalar(
            select(OperationalNotification).where(
                OperationalNotification.occurrence_id == other_occurrence
            )
        )
        other = db.scalar(
            select(OutboxEvent).where(OutboxEvent.notification_id == notification.id)
        ).id
    with pytest.raises(ApiError) as conflict:
        retry(s, other, command)
    assert conflict.value.code == "OUTBOX_COMMAND_CONFLICT"


def test_custom_operational_grants_never_authorize_outbox_admin(client, queued):
    from app.modules.access_profiles.models import AccessProfile, ProfilePermission

    s, identifier, _ = queued
    profile_id, user_id = uuid.uuid4(), uuid.uuid4()
    with s.factory() as db:
        profile = AccessProfile(
            id=profile_id, name="Fictício OC109", name_key="fictício oc109", active=True
        )
        db.add(profile)
        db.flush()
        db.add(
            ProfilePermission(
                profile_id=profile_id,
                permission_code="loadx.trips.read",
                delegable=True,
            )
        )
        db.add(
            User(
                id=user_id,
                name="Conta fictícia OC109",
                email=f"{user_id}@example.invalid",
                password_hash="fixture-only-no-password-login",
                role="CUSTOM",
                custom_profile_id=profile_id,
                active=True,
            )
        )
        db.commit()
    try:
        headers = issue_session_headers(s.factory, user_id)
        assert client.get(BASE, headers=headers).status_code == 403
        assert (
            client.post(
                f"{BASE}/{identifier}/retry",
                headers=headers,
                json={"command_id": str(uuid.uuid4())},
            ).status_code
            == 403
        )
    finally:
        with s.factory() as db:
            db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.execute(
                delete(ProfilePermission).where(
                    ProfilePermission.profile_id == profile_id
                )
            )
            db.execute(delete(AccessProfile).where(AccessProfile.id == profile_id))
            db.commit()
