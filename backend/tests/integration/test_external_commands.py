import json
import logging
import uuid
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from threading import Barrier, Event
from unittest.mock import patch

import pytest
from pydantic import SecretBytes
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.integrations.external_commands import (
    BoundExternalActorResolver,
    HmacExternalAuthenticator,
    TrustedIntegration,
)
from app.modules.customers.models import Customer
from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.service import TripService
from app.modules.drivers.models import Driver
from app.modules.external_commands.errors import ExternalCommandError
from app.modules.external_commands.models import ExternalCommand
from app.modules.external_commands.repository import ExternalCommandRepository
from app.modules.external_commands.schemas import CommandName
from app.modules.external_commands.service import ExternalCommandService
from app.modules.load_planning.models import LoadPlan, LoadPlanOrder
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product
from app.modules.status_history.models import StatusHistory
from app.modules.trucks.models import Truck
from app.modules.users.models import User
from tests.unit.test_delivery_service import create_user, prepare_receipt_delivery
from tests.unit.test_external_command_validation import KEY, NOW, command_body, sign


@dataclass
class Scenario:
    factory: Callable[[], Session]
    actors: dict[str, uuid.UUID]
    trip_id: uuid.UUID
    delivery_id: uuid.UUID
    driver_id: uuid.UUID

    def service(self, actor: str = "manager", **kwargs) -> ExternalCommandService:
        return ExternalCommandService(
            self.factory,
            HmacExternalAuthenticator(
                TrustedIntegration("fixture", frozenset(CommandName)), SecretBytes(KEY)
            ),
            BoundExternalActorResolver(
                {("fixture", "fixture-subject"): self.actors[actor]}
            ),
            clock=kwargs.pop("clock", lambda: NOW),
            **kwargs,
        )

    def body(self, **updates) -> bytes:
        return command_body(target_id=str(self.delivery_id), **updates)

    def counts(self) -> tuple[str, int, int]:
        with self.factory() as db:
            return (
                db.get(Delivery, self.delivery_id).status,
                db.scalar(
                    select(func.count())
                    .select_from(StatusHistory)
                    .where(StatusHistory.entity_id == self.delivery_id)
                ),
                db.scalar(
                    select(func.count())
                    .select_from(ExternalCommand)
                    .where(ExternalCommand.user_id.in_(self.actors.values()))
                ),
            )


@pytest.fixture
def scenario(postgres_engine: Engine) -> Generator[Scenario, None, None]:
    factory = sessionmaker(bind=postgres_engine, autoflush=False)
    with factory() as db:
        _service, manager, driver, trip, delivery, orders = prepare_receipt_delivery(db)
        actors = {"manager": manager.id}
        for name, role, driver_id in (
            ("admin", "ADMIN", None),
            ("checker", "CHECKER", None),
            ("unlinked", "DRIVER", None),
            ("driver", "DRIVER", driver.id),
            ("inactive", "LOGISTICS_MANAGER", None),
        ):
            user = create_user(db, role=role, driver_id=driver_id)
            if name == "inactive":
                user.active = False
            actors[name] = user.id
        other_driver = Driver(
            name="Outro Motorista Ficticio",
            document=uuid.uuid4().hex,
            phone="5512345670000",
            license_number=uuid.uuid4().hex,
            license_category="D",
            active=True,
        )
        db.add(other_driver)
        db.flush()
        actors["other_driver"] = create_user(
            db, role="DRIVER", driver_id=other_driver.id
        ).id
        plan_id = trip.load_plan_id
        truck_id = db.get(LoadPlan, plan_id).truck_id
        order_ids = tuple(order.id for order in orders)
        customer_id = orders[0].customer_id
        product_id = orders[0].items[0].product_id
        result = Scenario(factory, actors, trip.id, delivery.id, driver.id)
        other_driver_id = other_driver.id
        db.commit()
    try:
        yield result
    finally:
        with factory() as db:
            db.execute(
                delete(ExternalCommand).where(
                    ExternalCommand.user_id.in_(actors.values())
                )
            )
            db.execute(
                delete(StatusHistory).where(
                    StatusHistory.changed_by.in_(actors.values())
                )
            )
            db.execute(delete(Delivery).where(Delivery.trip_id == result.trip_id))
            db.execute(delete(Trip).where(Trip.id == result.trip_id))
            db.execute(
                delete(LoadPlanOrder).where(LoadPlanOrder.load_plan_id == plan_id)
            )
            db.execute(delete(LoadPlan).where(LoadPlan.id == plan_id))
            db.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
            db.execute(delete(Order).where(Order.id.in_(order_ids)))
            db.execute(delete(Product).where(Product.id == product_id))
            db.execute(delete(Customer).where(Customer.id == customer_id))
            db.execute(delete(Truck).where(Truck.id == truck_id))
            db.execute(delete(User).where(User.id.in_(actors.values())))
            db.execute(
                delete(Driver).where(Driver.id.in_((result.driver_id, other_driver_id)))
            )
            db.commit()


@pytest.mark.parametrize("actor", ("manager", "driver"))
def test_valid_command_uses_domain_and_replay_preserves_receipt_and_history(
    scenario, actor
):
    service = scenario.service(actor)
    body = scenario.body()
    before = scenario.counts()
    original = TripService.change_delivery_status
    calls = []

    def tracked(domain_service, target_id, status, *, current_user):
        calls.append((target_id, status, current_user.id))
        return original(domain_service, target_id, status, current_user=current_user)

    with patch.object(TripService, "change_delivery_status", tracked):
        first = service.process(body, sign(body))
        duplicate = service.process(body, sign(body))
    assert calls == [(scenario.delivery_id, "DELIVERED", scenario.actors[actor])]
    assert duplicate.id == first.id
    assert first.duplicate is False and duplicate.duplicate is True
    assert scenario.counts() == ("DELIVERED", before[1] + 1, 1)
    with scenario.factory() as db:
        row = db.get(ExternalCommand, first.id)
        assert row.completed_at == NOW
        assert row.user_id == scenario.actors[actor]
        assert row.event_hash != "fixture-event"
        assert row.fingerprint != body.decode()
        assert (
            db.get(Order, db.get(Delivery, scenario.delivery_id).order_id).status
            == "DELIVERED"
        )


@pytest.mark.parametrize(
    "actor", ("admin", "checker", "inactive", "unlinked", "other_driver")
)
def test_actor_rbac_and_object_binding_cannot_be_bypassed(scenario, actor):
    body = scenario.body()
    before = scenario.counts()
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_COMMAND_FORBIDDEN$"):
        scenario.service(actor).process(body, sign(body))
    assert scenario.counts() == before


def test_inactive_driver_and_missing_user_fail_closed(scenario):
    body = scenario.body()
    before = scenario.counts()
    with scenario.factory() as db:
        db.get(Driver, scenario.driver_id).active = False
        db.commit()
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_COMMAND_FORBIDDEN$"):
        scenario.service("driver").process(body, sign(body))
    service = scenario.service()
    service.actor_resolver = BoundExternalActorResolver(
        {("fixture", "fixture-subject"): uuid.uuid4()}
    )
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_COMMAND_FORBIDDEN$"):
        service.process(body, sign(body))
    assert scenario.counts() == before


@pytest.mark.parametrize("failure_point", ("before_domain", "after_domain_commit"))
def test_failure_rolls_back_claim_domain_and_history_and_allows_retry(
    scenario, monkeypatch, failure_point
):
    body = scenario.body()
    before = scenario.counts()

    def fail(*_args, **_kwargs):
        raise RuntimeError("sensitive-provider-token")

    with monkeypatch.context() as patcher:
        if failure_point == "before_domain":
            patcher.setattr(TripService, "get_trip", fail)
        else:
            patcher.setattr(ExternalCommandRepository, "complete", fail)
        with pytest.raises(ExternalCommandError, match="^EXTERNAL_PROCESSING_FAILED$"):
            scenario.service().process(body, sign(body))
    assert scenario.counts() == before
    with scenario.factory() as db:
        order = db.get(Order, db.get(Delivery, scenario.delivery_id).order_id)
        assert order.status == "IN_TRANSIT"
    receipt = scenario.service().process(body, sign(body))
    assert receipt.duplicate is False
    assert scenario.counts() == ("DELIVERED", before[1] + 1, 1)


def test_same_event_with_different_payload_or_resolved_actor_is_conflict(scenario):
    body = scenario.body()
    scenario.service().process(body, sign(body))
    before = scenario.counts()
    changed = scenario.body(command="START_DELIVERY")
    for service, candidate in (
        (scenario.service(), changed),
        (scenario.service("driver"), body),
    ):
        with pytest.raises(ExternalCommandError, match="^EXTERNAL_IDENTITY_CONFLICT$"):
            service.process(candidate, sign(candidate))
    assert scenario.counts() == before


def test_duplicate_rechecks_current_user_state_and_expiry(scenario):
    body = scenario.body()
    scenario.service().process(body, sign(body))
    with scenario.factory() as db:
        db.get(User, scenario.actors["manager"]).role = "CHECKER"
        db.commit()
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_COMMAND_FORBIDDEN$"):
        scenario.service().process(body, sign(body))
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_COMMAND_EXPIRED$"):
        scenario.service(clock=lambda: NOW + timedelta(minutes=5)).process(
            body, sign(body)
        )
    assert scenario.counts()[2] == 1


def test_expiry_while_domain_waits_rolls_back_internal_commit(scenario, monkeypatch):
    body = scenario.body()
    before = scenario.counts()
    time = [NOW]
    original = TripService.change_delivery_status

    def expiring(domain_service, *args, **kwargs):
        result = original(domain_service, *args, **kwargs)
        time[0] = NOW + timedelta(minutes=5)
        return result

    monkeypatch.setattr(TripService, "change_delivery_status", expiring)
    with pytest.raises(ExternalCommandError, match="^EXTERNAL_COMMAND_EXPIRED$"):
        scenario.service(clock=lambda: time[0]).process(body, sign(body))
    assert scenario.counts() == before


def test_concurrent_same_event_has_one_domain_execution_and_one_receipt(
    scenario, monkeypatch
):
    body = scenario.body()
    before = scenario.counts()
    barrier = Barrier(2)
    original_claim = ExternalCommandRepository.claim
    original_execute = TripService.change_delivery_status
    calls = []

    def simultaneous(repository, **kwargs):
        barrier.wait(timeout=5)
        return original_claim(repository, **kwargs)

    def counted(domain_service, *args, **kwargs):
        calls.append(1)
        return original_execute(domain_service, *args, **kwargs)

    monkeypatch.setattr(ExternalCommandRepository, "claim", simultaneous)
    monkeypatch.setattr(TripService, "change_delivery_status", counted)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(scenario.service().process, body, sign(body))
            for _ in range(2)
        ]
        receipts = [future.result(timeout=15) for future in futures]
    assert receipts[0].id == receipts[1].id
    assert sorted(receipt.duplicate for receipt in receipts) == [False, True]
    assert calls == [1]
    assert scenario.counts() == ("DELIVERED", before[1] + 1, 1)


def test_concurrent_retry_takes_over_after_first_transaction_rolls_back(
    scenario, monkeypatch
):
    body = scenario.body()
    claimed = Event()
    retry_attempted = Event()
    original = ExternalCommandRepository.complete

    def fail_first(repository, row, completed_at):
        if not claimed.is_set():
            claimed.set()
            assert retry_attempted.wait(timeout=5)
            raise RuntimeError("fixture failure after domain commit")
        return original(repository, row, completed_at)

    monkeypatch.setattr(ExternalCommandRepository, "complete", fail_first)

    def retry():
        assert claimed.wait(timeout=5)
        retry_attempted.set()
        return scenario.service().process(body, sign(body))

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(scenario.service().process, body, sign(body))
        second = executor.submit(retry)
        with pytest.raises(ExternalCommandError, match="^EXTERNAL_PROCESSING_FAILED$"):
            first.result(timeout=15)
        assert second.result(timeout=15).duplicate is False
    assert scenario.counts()[0] == "DELIVERED"
    assert scenario.counts()[2] == 1


def test_domain_invalid_transition_and_missing_target_are_predictable(scenario):
    before = scenario.counts()
    with scenario.factory() as db:
        trip = db.get(Trip, scenario.trip_id)
        trip.status = "SCHEDULED"
        trip.started_at = None
        db.commit()
    for body in (scenario.body(), command_body(target_id=str(uuid.uuid4()))):
        with pytest.raises(ExternalCommandError, match="^EXTERNAL_DOMAIN_REJECTED$"):
            scenario.service().process(body, sign(body))
    assert scenario.counts() == before


def test_start_commands_reuse_existing_domain_transitions(scenario, monkeypatch):
    with scenario.factory() as db:
        trip = db.get(Trip, scenario.trip_id)
        trip.status = "SCHEDULED"
        trip.started_at = None
        db.get(Delivery, scenario.delivery_id).status = "PENDING"
        for order in db.scalars(
            select(Order).where(
                Order.id.in_(
                    select(Delivery.order_id).where(
                        Delivery.trip_id == scenario.trip_id
                    )
                )
            )
        ):
            order.status = "PLANNED"
        db.commit()
    monkeypatch.setattr(
        LoadingReferenceService, "is_load_plan_finished", lambda *_: True
    )
    trip_body = command_body(command="START_TRIP", target_id=str(scenario.trip_id))
    delivery_body = scenario.body(event_id="delivery-start", command="START_DELIVERY")
    assert scenario.service().process(trip_body, sign(trip_body)).duplicate is False
    assert (
        scenario.service().process(delivery_body, sign(delivery_body)).duplicate
        is False
    )
    with scenario.factory() as db:
        assert db.get(Trip, scenario.trip_id).status == "IN_ROUTE"
        assert db.get(Delivery, scenario.delivery_id).status == "IN_DELIVERY"


def test_receipt_and_security_events_do_not_expose_external_secrets(scenario, caplog):
    body = scenario.body()
    with caplog.at_level(logging.INFO, logger="loadx.security"):
        receipt = scenario.service().process(body, sign(body))
    log = json.loads(caplog.records[-1].getMessage())
    assert set(log) == {
        "alert",
        "event",
        "occurred_at",
        "correlation_id",
        "command_id",
        "duplicate",
    }
    assert set(receipt.model_dump()) == {"id", "duplicate"}
    for sensitive in (
        sign(body),
        "fixture-subject",
        "fixture-event",
        KEY.hex(),
        body.decode(),
    ):
        assert sensitive not in caplog.text + receipt.model_dump_json()


def test_database_enforces_event_identity_independently_of_service(scenario):
    body = scenario.body()
    receipt = scenario.service().process(body, sign(body))
    with scenario.factory() as db:
        original = db.get(ExternalCommand, receipt.id)
        db.add(
            ExternalCommand(
                integration_id=original.integration_id,
                event_hash=original.event_hash,
                fingerprint=original.fingerprint,
                user_id=original.user_id,
                command=original.command,
                expires_at=original.expires_at,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    assert scenario.counts()[2] == 1
