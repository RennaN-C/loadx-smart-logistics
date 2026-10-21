"""OC90/OC109 composition with real commits and exclusively mock transport."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Event

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from app.integrations.outbox import MockOutboxTransport, PermanentDeliveryError
from app.modules.deliveries.models import Delivery, Trip
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.loading.models import LoadingSession, LoadingSessionItem
from app.modules.notifications.models import (
    NotificationRecipient,
    OperationalNotification,
)
from app.modules.notifications.outbox_models import (
    OutboxAttempt,
    OutboxEvent,
    OutboxRetryCommand,
)
from app.modules.notifications.outbox_service import OutboxService
from app.modules.notifications.service import OperationalNotificationService
from app.modules.notifications.worker import process_one
from app.modules.orders.models import Order
from app.modules.status_history.models import AuditEvent, StatusHistory
from tests.integration.oc90_helpers import seed_multi_flow
from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario
from tests.integration.test_messages_api import finish_loading


def rows(factory, *models):
    with factory() as db:
        return tuple(
            tuple(
                db.execute(
                    select(model.__table__).order_by(
                        *model.__table__.primary_key.columns
                    )
                ).all()
            )
            for model in models
        )


def domain_snapshot(factory):
    return rows(
        factory,
        LoadPlan,
        LoadPlanOrder,
        LoadPlanItem,
        LoadingSession,
        LoadingSessionItem,
        Trip,
        Delivery,
        Order,
        StatusHistory,
    )


@pytest.fixture
def flow(client, session_factory, monkeypatch):
    # Model a process that committed its fact and stopped before inline dispatch.
    # Worker must recover from the database, never Session.info or a real channel.
    monkeypatch.setattr(
        OperationalNotificationService,
        "dispatch_after_commit",
        staticmethod(lambda db: None),
    )
    s = seed_multi_flow(client, session_factory)
    s.approve()
    s.prepare_loadings()
    s.finish_loading(0)
    s.finish_loading(1)
    s.trips = [s.create_trip(index) for index in range(2)]
    return s


def test_two_legs_commit_outbox_once_and_worker_preserves_physical_execution(flow):
    s = flow
    s.trip_status(0, "IN_ROUTE")
    s.trip_status(0, "IN_ROUTE")
    assert s.status() == "IN_TRANSIT"
    before = domain_snapshot(s.factory)
    entered, resume = Event(), Event()

    class PausingMock(MockOutboxTransport):
        def send(self, envelope):
            entered.set()
            assert resume.wait(timeout=10)
            return super().send(envelope)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(process_one, s.factory, PausingMock())
        try:
            assert entered.wait(timeout=10)
            with s.factory() as db:
                event = db.scalar(select(OutboxEvent))
                assert event.status == "PROCESSING"
                assert event.generation == 1
                assert event.lease_expires_at is not None
                # The other part has an independent FINISHED checklist and its
                # physical snapshot stays protected while the worker runs.
                plan_id = uuid.UUID(s.parts[1]["load_plan"]["id"])

                def attempt_snapshot_update():
                    db.execute(
                        update(LoadPlanItem)
                        .where(LoadPlanItem.load_plan_id == plan_id)
                        .values(position_x_cm=1)
                    )

                with pytest.raises(IntegrityError) as error:
                    attempt_snapshot_update()
                assert (
                    error.value.orig.diag.constraint_name
                    == "ck_load_plans__operational_snapshot"
                )
                db.rollback()
            assert domain_snapshot(s.factory) == before
        finally:
            resume.set()
        assert future.result(timeout=20)
    assert domain_snapshot(s.factory) == before
    assert not process_one(s.factory, MockOutboxTransport())

    s.complete_delivery(0)
    assert s.status() == "IN_TRANSIT"
    s.trip_status(0, "FINISHED")
    s.trip_status(1, "IN_ROUTE")
    s.trip_status(1, "IN_ROUTE")
    before = domain_snapshot(s.factory)
    assert process_one(s.factory, MockOutboxTransport())
    assert domain_snapshot(s.factory) == before
    receipt = s.complete_delivery(1)
    assert s.status() == "DELIVERED"
    assert (
        s.request("POST", f"/deliveries/{receipt['delivery_id']}/receipt", {})
        == receipt
    )
    s.trip_status(1, "FINISHED")
    assert not process_one(s.factory, MockOutboxTransport())
    with s.factory() as db:
        notifications = db.scalars(select(OperationalNotification)).all()
        events = db.scalars(select(OutboxEvent)).all()
        assert len(notifications) == len(events) == 2
        assert {n.trip_id for n in notifications} == {
            uuid.UUID(t["id"]) for t in s.trips
        }
        assert {e.notification_id for e in events} == {n.id for n in notifications}
        assert {n.mock_status for n in notifications} == {"SIMULATED"}
        assert {e.status for e in events} == {"SUCCEEDED"}
        assert db.scalar(select(func.count()).select_from(OutboxAttempt)) == 2
        assert db.scalar(select(func.count()).select_from(NotificationRecipient)) > 0
        for n in notifications:
            history = db.get(StatusHistory, n.status_history_id)
            assert (
                history.entity_type,
                history.entity_id,
                history.old_status,
                history.new_status,
            ) == ("TRIP", n.trip_id, "SCHEDULED", "IN_ROUTE")
        order_history = db.scalars(
            select(StatusHistory).where(
                StatusHistory.entity_id == uuid.UUID(s.order["id"])
            )
        ).all()
        transitions = [(h.old_status, h.new_status) for h in order_history]
        assert transitions.count(("PLANNED", "IN_TRANSIT")) == 1
        assert transitions.count(("IN_TRANSIT", "DELIVERED")) == 1
    before = rows(
        s.factory, OperationalNotification, OutboxEvent, OutboxAttempt, StatusHistory
    )
    migration = import_module(
        "migrations.versions.20261020_0028_delivery_distribution_parts"
    )
    with (
        s.factory() as db,
        Operations.context(MigrationContext.configure(db.connection())),
        pytest.raises(RuntimeError, match="OC90 downgrade blocked"),
    ):
        migration.downgrade()
    assert (
        rows(
            s.factory,
            OperationalNotification,
            OutboxEvent,
            OutboxAttempt,
            StatusHistory,
        )
        == before
    )


@pytest.mark.parametrize("after_insert", [False, True])
def test_failed_start_rolls_back_domain_notification_outbox_and_retries_once(
    flow, monkeypatch, after_insert
):
    s = flow
    before = domain_snapshot(s.factory)
    original = OutboxService.stage

    def fail(service, notification):
        if after_insert:
            original(service, notification)
        raise RuntimeError("fictitious staging failure")

    with monkeypatch.context() as patch:
        patch.setattr(OutboxService, "stage", fail)
        s.trip_status(0, "IN_ROUTE", expected=500)
    assert domain_snapshot(s.factory) == before
    with s.factory() as db:
        for model in (
            OperationalNotification,
            NotificationRecipient,
            OutboxEvent,
            OutboxAttempt,
        ):
            assert db.scalar(select(func.count()).select_from(model)) == 0
    s.trip_status(0, "IN_ROUTE")
    s.trip_status(0, "IN_ROUTE")
    assert s.status() == "IN_TRANSIT"
    assert process_one(s.factory, MockOutboxTransport())
    assert not process_one(s.factory, MockOutboxTransport())
    with s.factory() as db:
        for model in (OperationalNotification, OutboxEvent, OutboxAttempt):
            assert db.scalar(select(func.count()).select_from(model)) == 1


def test_oc90_upgrade_downgrade_preserves_existing_outbox_receipts_attempts_and_audit(
    client, session_factory, monkeypatch
):
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    finish_loading(client, scenario)
    response = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=scenario.manager_headers,
    )
    assert response.status_code == 200, response.text
    # Adopt the existing mock attempt, then record an administrative retry of
    # a second, failed mock fact without deleting or rewriting any history.
    monkeypatch.setattr(
        OperationalNotificationService,
        "dispatch_after_commit",
        staticmethod(lambda db: None),
    )
    occurrence = client.post(
        "/api/v1/occurrences",
        json={"trip_id": trip["id"], "type": "DELAY", "description": "Fato fictício"},
        headers=scenario.manager_headers,
    )
    assert occurrence.status_code == 201, occurrence.text

    class RejectingMock(MockOutboxTransport):
        def send(self, envelope):
            raise PermanentDeliveryError

    # Adoption can return False even with another due event; run bounded cycles.
    for _ in range(2):
        process_one(session_factory, RejectingMock())
    with session_factory() as db:
        event_id = db.scalar(
            select(OutboxEvent.id)
            .join(OperationalNotification)
            .where(
                OperationalNotification.occurrence_id
                == uuid.UUID(occurrence.json()["id"])
            )
        )
        assert db.get(OutboxEvent, event_id).status == "TERMINAL"
    command = {"command_id": str(uuid.uuid4())}
    for _ in range(2):
        retry = client.post(
            f"/api/v1/outbox-events/{event_id}/retry",
            json=command,
            headers=scenario.admin_headers,
        )
        assert retry.status_code == 200, retry.text
    assert process_one(session_factory, MockOutboxTransport())
    models = (
        OperationalNotification,
        NotificationRecipient,
        OutboxEvent,
        OutboxAttempt,
        OutboxRetryCommand,
        AuditEvent,
        StatusHistory,
    )
    before = rows(session_factory, *models)
    assert len(before[0]) == len(before[2]) == 2
    assert len(before[3]) == 3
    assert len(before[4]) == len(before[5]) == 1
    migration = import_module(
        "migrations.versions.20261020_0028_delivery_distribution_parts"
    )
    with session_factory() as db:
        with Operations.context(MigrationContext.configure(db.connection())):
            migration.downgrade()
            migration.upgrade()
        db.commit()
    assert rows(session_factory, *models) == before
    with session_factory() as db:
        assert (
            db.scalar(text("SELECT version_num FROM alembic_version"))
            == "20261021_0030"
        )
        assert (
            db.scalar(text("SELECT to_regclass('public.outbox_events')"))
            == "outbox_events"
        )
