"""OC84 invariants on PostgreSQL 16, with independent committed connections."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.integrations.whatsapp import MockWhatsAppProvider, OutgoingWhatsAppMessage
from app.modules.deliveries.models import Trip
from app.modules.deliveries.service import TripService
from app.modules.drivers.models import Driver
from app.modules.notifications.models import NotificationRecipient
from app.modules.notifications.models import OperationalNotification as Notification
from app.modules.notifications.repository import (
    OperationalNotificationRepository as Repository,
)
from app.modules.notifications.service import OperationalNotificationService as Service
from app.modules.occurrences.models import Occurrence
from app.modules.occurrences.schemas import OccurrenceCreate
from app.modules.occurrences.service import OccurrenceService
from app.modules.orders.models import Order
from app.modules.status_history.models import StatusHistory
from app.modules.users.models import User
from tests.integration.test_external_commands import scenario

__all__ = ("scenario",)


def register(s, service=None, db=None):
    if db is None:
        with s.factory() as owned:
            return register(s, service, owned)
    result = OccurrenceService(db, notification_service=service).register_occurrence(
        OccurrenceCreate(
            trip_id=s.trip_id, type="DELAY", description="Fato fictício OC84."
        ),
        current_user=db.get(User, s.actors["manager"]),
    )
    return result.id


def row_for(s, occurrence_id):
    with s.factory() as db:
        return db.scalar(
            select(Notification).where(Notification.occurrence_id == occurrence_id)
        )


def counts(s):
    with s.factory() as db:
        return (
            db.scalar(
                select(func.count())
                .select_from(Occurrence)
                .where(Occurrence.trip_id == s.trip_id)
            ),
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.trip_id == s.trip_id,
                    Notification.event_type == "OCCURRENCE_REGISTERED",
                )
            ),
        )


def test_record_is_durable_after_service_restart_and_is_not_an_outbound_receipt(
    scenario,
):
    s = scenario
    occurrence_id = register(s)
    row = row_for(s, occurrence_id)
    assert row.mock_status == "NOT_ATTEMPTED"
    assert row.recipient_driver_id == s.driver_id
    assert row.status_history_id is None
    assert row.claimed_at is None
    assert row.completed_at is None
    with s.factory() as restarted:
        loaded = Repository(restarted).get(row.id)
        assert loaded.occurrence_id == occurrence_id
        assert set(loaded.__table__.columns.keys()) == {
            "id",
            "event_type",
            "status_history_id",
            "occurrence_id",
            "trip_id",
            "recipient_driver_id",
            "correlation_id",
            "created_at",
            "mock_status",
            "claimed_at",
            "completed_at",
        }


def test_same_origin_registration_is_unique_with_independent_connections(scenario):
    s = scenario
    occurrence_id = register(s)
    barrier = Barrier(2)

    def record():
        with s.factory() as db:
            barrier.wait(timeout=10)
            identifier = Service().stage(
                db,
                event_type="OCCURRENCE_REGISTERED",
                trip_id=s.trip_id,
                recipient_driver_id=s.driver_id,
                occurrence_id=occurrence_id,
            )
            db.commit()
            return identifier

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: record(), range(2)))
    assert results == [row_for(s, occurrence_id).id] * 2
    assert counts(s) == (1, 1)


def test_atomic_claim_allows_one_mock_under_concurrency(scenario):
    s = scenario
    row = row_for(s, register(s))
    provider = MockWhatsAppProvider()
    service = Service(provider)
    barrier = Barrier(2)

    def dispatch():
        barrier.wait(timeout=10)
        service.dispatch(row.id, s.factory)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: dispatch(), range(2)))
    assert len(provider.sent_messages) == 1
    with s.factory() as db:
        result = Repository(db).get(row.id)
        assert result.mock_status == "SIMULATED"
        assert result.claimed_at is not None
        assert result.completed_at is not None


def test_notification_failure_rolls_back_occurrence(scenario, monkeypatch):
    original = Repository.record

    def fail(repository, **values):
        original(repository, **values)
        raise RuntimeError("fixture record failed")

    monkeypatch.setattr(Repository, "record", fail)
    provider = MockWhatsAppProvider()
    channel = Service(provider)
    with pytest.raises(RuntimeError, match="fixture record failed"):
        register(scenario, channel)
    assert counts(scenario) == (0, 0)
    assert provider.sent_messages == []


def prepare_scheduled(s):
    with s.factory() as db:
        # Arrange a pristine scheduled-trip fixture, removing its setup transition.
        db.execute(
            delete(NotificationRecipient).where(
                NotificationRecipient.notification_id.in_(
                    select(Notification.id).where(Notification.trip_id == s.trip_id)
                )
            )
        )
        db.execute(delete(Notification).where(Notification.trip_id == s.trip_id))
        db.execute(
            delete(StatusHistory).where(
                StatusHistory.entity_id == s.trip_id,
                StatusHistory.new_status == "IN_ROUTE",
            )
        )
        trip = db.get(Trip, s.trip_id)
        trip.status = "SCHEDULED"
        trip.started_at = None
        for delivery in TripService(db).repository.list_deliveries_for_update(
            s.trip_id
        ):
            db.get(Order, delivery.order_id).status = "PLANNED"
        db.commit()


class FinishedLoading:
    def is_load_plan_finished(self, _id):
        return True


def test_trip_start_uses_exact_history_and_same_status_does_not_duplicate(scenario):
    s = scenario
    prepare_scheduled(s)
    provider = MockWhatsAppProvider()
    with s.factory() as db:
        service = TripService(
            db,
            notification_service=Service(provider),
            loading_reference_service=FinishedLoading(),
        )
        actor = db.get(User, s.actors["manager"])
        service.change_trip_status(s.trip_id, "IN_ROUTE", current_user=actor)
        service.change_trip_status(s.trip_id, "IN_ROUTE", current_user=actor)
    with s.factory() as db:
        rows = list(
            db.scalars(select(Notification).where(Notification.trip_id == s.trip_id))
        )
        assert len(rows) == 1
        history = db.get(StatusHistory, rows[0].status_history_id)
        assert (
            history.entity_type,
            history.entity_id,
            history.old_status,
            history.new_status,
        ) == ("TRIP", s.trip_id, "SCHEDULED", "IN_ROUTE")
        assert rows[0].mock_status == "SIMULATED"
    assert len(provider.sent_messages) == 1


def test_notification_failure_rolls_back_trip_and_history(scenario, monkeypatch):
    s = scenario
    prepare_scheduled(s)

    def fail(*args, **kwargs):
        raise RuntimeError("fixture notification failure")

    monkeypatch.setattr(Repository, "record", fail)
    with s.factory() as db:
        service = TripService(db, loading_reference_service=FinishedLoading())
        actor = db.get(User, s.actors["manager"])
        with pytest.raises(RuntimeError, match="fixture notification failure"):
            service.change_trip_status(s.trip_id, "IN_ROUTE", current_user=actor)
    with s.factory() as db:
        assert db.get(Trip, s.trip_id).status == "SCHEDULED"
        assert (
            db.scalar(
                select(func.count())
                .select_from(StatusHistory)
                .where(
                    StatusHistory.entity_id == s.trip_id,
                    StatusHistory.new_status == "IN_ROUTE",
                )
            )
            == 0
        )


@pytest.mark.parametrize("rollback", [False, True])
def test_external_savepoint_does_not_authorize_mock(scenario, rollback):
    s = scenario
    provider = MockWhatsAppProvider()

    class OuterRollback(Exception):
        pass

    try:
        with s.factory() as owner:
            with owner.begin():
                with Session(
                    bind=owner.connection(), join_transaction_mode="create_savepoint"
                ) as domain:
                    occurrence_id = register(s, Service(provider), domain)
                    Service.transfer_staged(domain, owner)
                assert counts(s) == (0, 0)
                assert provider.sent_messages == []
                if rollback:
                    raise OuterRollback
            Service.dispatch_after_commit(owner)
    except OuterRollback:
        pass
    if rollback:
        assert counts(s) == (0, 0)
        assert provider.sent_messages == []
    else:
        assert row_for(s, occurrence_id).mock_status == "SIMULATED"
        assert len(provider.sent_messages) == 1


def test_claim_is_visible_before_mock_and_provider_failure_keeps_domain(scenario):
    s = scenario
    observed = []

    class FailingMock(MockWhatsAppProvider):
        def send_response(self, message: OutgoingWhatsAppMessage):
            with s.factory() as observer:
                observed.append(
                    observer.scalar(
                        select(Notification.mock_status).where(
                            Notification.trip_id == s.trip_id,
                            Notification.event_type == "OCCURRENCE_REGISTERED",
                        )
                    )
                )
            raise RuntimeError("fixture unavailable; private-phone private-content")

    occurrence_id = register(s, Service(FailingMock()))
    assert observed == ["ATTEMPT_CLAIMED"]
    assert row_for(s, occurrence_id).mock_status == "FAILED"
    assert counts(s) == (1, 1)


@pytest.mark.parametrize("reason", ["missing_phone", "inactive", "binding_changed"])
def test_no_eligible_recipient_keeps_original_identity_without_mock(scenario, reason):
    s = scenario
    row = row_for(s, register(s))
    with s.factory() as db:
        driver = db.get(Driver, s.driver_id)
        if reason == "missing_phone":
            driver.phone = "  "
        if reason == "inactive":
            driver.active = False
        if reason == "binding_changed":
            db.get(Trip, s.trip_id).driver_id = db.get(
                User, s.actors["other_driver"]
            ).driver_id
        db.commit()
    provider = MockWhatsAppProvider()
    Service(provider).dispatch(row.id, s.factory)
    with s.factory() as db:
        persisted = db.get(Notification, row.id)
        assert persisted.mock_status == "NO_RECIPIENT"
        assert persisted.recipient_driver_id == s.driver_id
        # Restore the shared fixture's original relationship for cleanup.
        db.get(Trip, s.trip_id).driver_id = s.driver_id
        db.get(Driver, s.driver_id).active = True
        db.commit()
    assert provider.sent_messages == []


def test_crash_after_claim_never_automatically_retries(scenario):
    s = scenario
    row = row_for(s, register(s))
    with s.factory() as db:
        assert Repository(db).claim(row.id)
        db.commit()
    provider = MockWhatsAppProvider()
    Service(provider).dispatch(row.id, s.factory)
    with s.factory() as db:
        assert db.get(Notification, row.id).mock_status == "ATTEMPT_CLAIMED"
    assert provider.sent_messages == []


def test_uncertain_result_after_mock_stays_claimed_and_is_not_retried(
    scenario, monkeypatch
):
    s = scenario
    row = row_for(s, register(s))
    provider = MockWhatsAppProvider()

    def fail(*args, **kwargs):
        raise RuntimeError("fixture result persistence failure")

    monkeypatch.setattr(Repository, "complete", fail)
    service = Service(provider)
    service.dispatch(row.id, s.factory)
    service.dispatch(row.id, s.factory)
    with s.factory() as db:
        assert db.get(Notification, row.id).mock_status == "ATTEMPT_CLAIMED"
    assert len(provider.sent_messages) == 1


@pytest.mark.parametrize(
    "violation",
    [
        "wrong_trip_history",
        "wrong_transition",
        "forged_result",
        "identity_change",
        "duplicate",
        "retry_failed",
    ],
)
def test_native_constraints_reject_invalid_notification_writes(scenario, violation):
    s = scenario
    row = row_for(s, register(s))
    with s.factory() as db:
        if violation in {"wrong_trip_history", "wrong_transition"}:
            history = StatusHistory(
                id=uuid.uuid4(),
                entity_type="TRIP",
                entity_id=uuid.uuid4()
                if violation == "wrong_trip_history"
                else s.trip_id,
                old_status="SCHEDULED"
                if violation == "wrong_trip_history"
                else "IN_ROUTE",
                new_status="IN_ROUTE",
                changed_by=s.actors["manager"],
            )
            db.add(history)
            db.flush()
            statement = insert(Notification).values(
                id=uuid.uuid4(),
                event_type="TRIP_STARTED",
                status_history_id=history.id,
                trip_id=s.trip_id,
                recipient_driver_id=s.driver_id,
                correlation_id=uuid.uuid4(),
            )
        elif violation == "forged_result":
            statement = (
                update(Notification)
                .where(Notification.id == row.id)
                .values(
                    mock_status="SIMULATED",
                    claimed_at=func.now(),
                    completed_at=func.now(),
                )
            )
        elif violation == "identity_change":
            statement = (
                update(Notification)
                .where(Notification.id == row.id)
                .values(correlation_id=uuid.uuid4())
            )
        elif violation == "duplicate":
            statement = insert(Notification).values(
                id=uuid.uuid4(),
                event_type=row.event_type,
                occurrence_id=row.occurrence_id,
                trip_id=row.trip_id,
                recipient_driver_id=row.recipient_driver_id,
                correlation_id=uuid.uuid4(),
            )
        else:
            Repository(db).claim(row.id)
            Repository(db).complete(row.id, "FAILED")
            statement = (
                update(Notification)
                .where(Notification.id == row.id)
                .values(mock_status="NOT_ATTEMPTED", claimed_at=None, completed_at=None)
            )
        with pytest.raises(IntegrityError):
            db.execute(statement)
        db.rollback()


def test_external_start_replay_dispatches_only_after_receipt_commit(
    scenario, monkeypatch
):
    from app.modules.external_commands import service as command_module
    from app.modules.external_commands.models import ExternalCommand
    from app.modules.loading.reference_service import LoadingReferenceService
    from tests.unit.test_external_command_validation import command_body, sign

    s = scenario
    prepare_scheduled(s)
    observed = []

    class ObservingMock(MockWhatsAppProvider):
        def send_response(self, message):
            with s.factory() as db:
                assert db.get(Trip, s.trip_id).status == "IN_ROUTE"
                assert (
                    db.scalar(
                        select(ExternalCommand.completed_at).where(
                            ExternalCommand.user_id == s.actors["manager"]
                        )
                    )
                    is not None
                )
                observed.append(
                    db.scalar(
                        select(Notification.mock_status).where(
                            Notification.trip_id == s.trip_id
                        )
                    )
                )
            return super().send_response(message)

    provider = ObservingMock()
    monkeypatch.setattr(command_module, "get_whatsapp_provider", lambda: provider)
    monkeypatch.setattr(
        LoadingReferenceService, "is_load_plan_finished", lambda *args: True
    )
    body = command_body(command="START_TRIP", target_id=str(s.trip_id))
    service = s.service()
    first = service.process(body, sign(body))
    duplicate = service.process(body, sign(body))
    assert duplicate.id == first.id
    assert duplicate.duplicate
    assert observed == ["ATTEMPT_CLAIMED"]
    assert len(provider.sent_messages) == 1
    with s.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.trip_id == s.trip_id)
            )
            == 1
        )


def test_external_failure_after_inner_commit_rolls_back_notification_and_does_not_mock(
    scenario, monkeypatch
):
    from app.modules.external_commands import service as command_module
    from app.modules.external_commands.errors import ExternalCommandError
    from app.modules.loading.reference_service import LoadingReferenceService
    from tests.unit.test_external_command_validation import command_body, sign

    s = scenario
    prepare_scheduled(s)
    provider = MockWhatsAppProvider()
    monkeypatch.setattr(command_module, "get_whatsapp_provider", lambda: provider)
    monkeypatch.setattr(
        LoadingReferenceService, "is_load_plan_finished", lambda *args: True
    )
    original = TripService.change_trip_status

    def fail_after_savepoint(service, *args, **kwargs):
        result = original(service, *args, **kwargs)
        assert result.status == "IN_ROUTE"
        with s.factory() as observer:
            assert observer.get(Trip, s.trip_id).status == "SCHEDULED"
            assert (
                observer.scalar(
                    select(func.count())
                    .select_from(Notification)
                    .where(Notification.trip_id == s.trip_id)
                )
                == 0
            )
        raise RuntimeError("fixture outer failure")

    monkeypatch.setattr(TripService, "change_trip_status", fail_after_savepoint)
    body = command_body(command="START_TRIP", target_id=str(s.trip_id))
    service = s.service()
    signature = sign(body)
    with pytest.raises(ExternalCommandError):
        service.process(body, signature)
    assert provider.sent_messages == []
    with s.factory() as db:
        assert db.get(Trip, s.trip_id).status == "SCHEDULED"
        assert (
            db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.trip_id == s.trip_id)
            )
            == 0
        )


def test_populated_downgrade_refuses_history_loss(scenario):
    from importlib import import_module

    migration = import_module(
        "migrations.versions.20261020_0025_operational_notifications"
    )
    occurrence_id = register(scenario)
    with scenario.factory() as db:
        connection = db.connection()
        with pytest.raises(RuntimeError, match="OC84 downgrade blocked"):
            migration.ensure_safe_downgrade(connection)
    assert row_for(scenario, occurrence_id) is not None


def test_referenced_occurrence_cannot_be_moved_to_another_trip_by_sql(scenario):
    occurrence_id = register(scenario)
    statement = (
        update(Occurrence)
        .where(Occurrence.id == occurrence_id)
        .values(trip_id=uuid.uuid4())
    )
    with scenario.factory() as db:
        with pytest.raises(IntegrityError):
            db.execute(statement)
        db.rollback()


def test_connection_bound_dispatch_cannot_claim_or_simulate_before_outer_commit(
    scenario,
):
    from sqlalchemy.orm import sessionmaker

    s = scenario
    row = row_for(s, register(s))
    provider = MockWhatsAppProvider()
    with s.factory() as owner, owner.begin():
        nested_factory = sessionmaker(
            bind=owner.connection(), join_transaction_mode="create_savepoint"
        )
        Service(provider).dispatch(row.id, nested_factory)
        assert provider.sent_messages == []
        with s.factory() as observer:
            assert observer.get(Notification, row.id).mock_status == "NOT_ATTEMPTED"


def test_crash_after_domain_commit_before_claim_preserves_unattempted_record(
    scenario, monkeypatch
):
    class ProcessStopped(BaseException):
        pass

    provider = MockWhatsAppProvider()

    def stop_before_claim(*args):
        raise ProcessStopped

    monkeypatch.setattr(Service, "dispatch", stop_before_claim)
    channel = Service(provider)
    with pytest.raises(ProcessStopped):
        register(scenario, channel)
    assert counts(scenario) == (1, 1)
    with scenario.factory() as db:
        row = db.scalar(
            select(Notification).where(
                Notification.trip_id == scenario.trip_id,
                Notification.event_type == "OCCURRENCE_REGISTERED",
            )
        )
        assert row.mock_status == "NOT_ATTEMPTED"
        assert row.claimed_at is None
    assert provider.sent_messages == []


def test_replay_after_commit_without_dispatch_does_not_recover_or_repeat_attempt(
    scenario, monkeypatch
):
    from app.modules.external_commands import service as command_module
    from app.modules.loading.reference_service import LoadingReferenceService
    from tests.unit.test_external_command_validation import command_body, sign

    s = scenario
    prepare_scheduled(s)
    provider = MockWhatsAppProvider()
    monkeypatch.setattr(command_module, "get_whatsapp_provider", lambda: provider)
    monkeypatch.setattr(
        LoadingReferenceService, "is_load_plan_finished", lambda *args: True
    )
    body = command_body(command="START_TRIP", target_id=str(s.trip_id))
    original = Service.dispatch_after_commit
    monkeypatch.setattr(Service, "dispatch_after_commit", lambda db: None)
    first = s.service().process(body, sign(body))
    monkeypatch.setattr(Service, "dispatch_after_commit", original)
    duplicate = s.service().process(body, sign(body))
    assert first.id == duplicate.id
    assert duplicate.duplicate
    with s.factory() as db:
        rows = list(
            db.scalars(select(Notification).where(Notification.trip_id == s.trip_id))
        )
        assert len(rows) == 1
        assert rows[0].mock_status == "NOT_ATTEMPTED"
    assert provider.sent_messages == []


@pytest.mark.parametrize("event_type", ["TRIP_STARTED", "OCCURRENCE_REGISTERED"])
def test_origin_cannot_change_concurrently_with_notification_registration(
    scenario, event_type
):
    s = scenario
    occurrence_id = register(s)
    with s.factory() as reader:
        row = reader.scalar(
            select(Notification).where(
                Notification.trip_id == s.trip_id,
                Notification.event_type == event_type,
            )
        )
    if event_type == "TRIP_STARTED":
        statement = (
            update(StatusHistory)
            .where(StatusHistory.id == row.status_history_id)
            .values(entity_id=uuid.uuid4())
        )
    else:
        statement = (
            update(Occurrence)
            .where(Occurrence.id == occurrence_id)
            .values(trip_id=uuid.uuid4())
        )

    def change_source():
        with s.factory() as writer:
            writer.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError) as blocked:
                writer.execute(statement)
            assert blocked.value.orig.sqlstate == "55P03"
            writer.rollback()

    with s.factory() as registration:
        Service().stage(
            registration,
            event_type=row.event_type,
            trip_id=row.trip_id,
            recipient_driver_id=row.recipient_driver_id,
            occurrence_id=row.occurrence_id,
            status_history_id=row.status_history_id,
        )
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(change_source).result(timeout=10)
        registration.commit()
    with s.factory() as writer:
        with pytest.raises(IntegrityError) as rejected:
            writer.execute(statement)
        assert rejected.value.orig.sqlstate == "23514"
        writer.rollback()
