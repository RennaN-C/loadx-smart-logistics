import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.schemas import TripCreate
from app.modules.deliveries.service import TripService
from app.modules.drivers.models import Driver
from app.modules.load_planning.models import LoadPlan, LoadPlanItem
from app.modules.load_planning.reference_service import LoadPlanReferenceService
from app.modules.loading.service import LoadingService
from app.modules.notifications.models import (
    NotificationRecipient,
    OperationalNotification,
)
from app.modules.orders.models import Order
from app.modules.status_history.models import StatusHistory
from app.modules.users.models import User
from tests.integration.test_load_distributions import distribution_scenario

__all__ = ("distribution_scenario",)


def test_concurrent_last_legs_serialize_order_and_record_one_completion(
    distribution_scenario,
):
    s = distribution_scenario
    result = s.create()
    approved = s.post(f"/{result['id']}/approve").json()
    parts = sorted(approved["parts"], key=lambda p: p["id"])
    driver_ids, trip_ids, delivery_ids = [], [], []
    try:
        with s.factory() as db:
            drivers = [
                Driver(
                    name="Fictício concorrência",
                    document=uuid.uuid4().hex,
                    phone="11900000000",
                    license_number=uuid.uuid4().hex,
                    license_category="D",
                    active=True,
                )
                for _ in parts
            ]
            db.add_all(drivers)
            db.commit()
            driver_ids = [driver.id for driver in drivers]
            manager = db.get(User, s.user.id)
            service = TripService(db)
            loading_service = LoadingService(db)
            for index, part in enumerate(parts):
                plan_id = uuid.UUID(part["load_plan"]["id"])
                loading = loading_service.create_session(plan_id)
                loading_service.change_status(loading.id, "IN_PROGRESS")
                for item in loading.items:
                    loading_service.change_item_status(loading.id, item.id, "CHECKED")
                loading_service.change_status(loading.id, "FINISHED")
                trip = service.create_trip(
                    TripCreate(load_plan_id=plan_id, driver_id=driver_ids[index]),
                    changed_by=s.user.id,
                )
                trip_ids.append(trip.id)
                delivery_ids.append(trip.deliveries[0].id)
                service.change_trip_status(trip.id, "IN_ROUTE", current_user=manager)
                service.change_delivery_status(
                    delivery_ids[-1], "IN_DELIVERY", current_user=manager
                )
        barrier = Barrier(2)

        def complete(delivery_id):
            with s.factory() as db:
                manager = db.get(User, s.user.id)
                order_snapshot = db.get(Order, s.source.order_id)
                delivery_snapshot = db.get(Delivery, delivery_id)
                assert order_snapshot.status == "IN_TRANSIT"
                assert delivery_snapshot.status == "IN_DELIVERY"
                barrier.wait(timeout=10)
                return TripService(db).register_delivery_receipt(
                    delivery_id, current_user=manager
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(complete, identifier) for identifier in delivery_ids
            ]
            receipts = [future.result(timeout=20) for future in futures]
        assert receipts[0].id != receipts[1].id
        assert s.order_status() == "DELIVERED"
        with s.factory() as db:
            history = db.scalars(
                select(StatusHistory).where(
                    StatusHistory.entity_id == s.source.order_id
                )
            ).all()
            assert [(h.old_status, h.new_status) for h in history].count(
                ("PLANNED", "IN_TRANSIT")
            ) == 1
            assert [(h.old_status, h.new_status) for h in history].count(
                ("IN_TRANSIT", "DELIVERED")
            ) == 1
            service = TripService(db)
            manager = db.get(User, s.user.id)
            for identifier, receipt in zip(delivery_ids, receipts, strict=True):
                assert (
                    service.register_delivery_receipt(identifier, current_user=manager)
                    == receipt
                )
                part = LoadPlanReferenceService(db).get_distribution_order_for_part(
                    db.get(Delivery, identifier).distribution_part_id, s.source.order_id
                )
                assert len(part.part_ids) == 2
            for identifier in trip_ids:
                assert (
                    service.change_trip_status(
                        identifier, "FINISHED", current_user=manager
                    ).status
                    == "FINISHED"
                )
    finally:
        # The owning distribution fixture cleans its physical graph afterwards.
        with s.factory() as db:
            notifications = select(OperationalNotification.id).where(
                OperationalNotification.trip_id.in_(trip_ids)
            )
            db.execute(
                delete(NotificationRecipient).where(
                    NotificationRecipient.notification_id.in_(notifications)
                )
            )
            db.execute(
                delete(OperationalNotification).where(
                    OperationalNotification.trip_id.in_(trip_ids)
                )
            )
            db.execute(delete(Delivery).where(Delivery.trip_id.in_(trip_ids)))
            db.execute(delete(Trip).where(Trip.id.in_(trip_ids)))
            db.execute(delete(Driver).where(Driver.id.in_(driver_ids)))
            db.commit()


def test_loading_parent_lock_rejects_child_delete_without_fk_deadlock(
    distribution_scenario, monkeypatch
):
    s = distribution_scenario
    result = s.create()
    approved = s.post(f"/{result['id']}/approve").json()
    plan_id = uuid.UUID(approved["parts"][0]["load_plan"]["id"])
    with s.factory() as db:
        item_ids = set(
            db.scalars(
                select(LoadPlanItem.id).where(LoadPlanItem.load_plan_id == plan_id)
            )
        )
    locked, resume = Event(), Event()
    original = LoadPlanReferenceService.get_loading_items

    def pause_after_parent_lock(service, identifier):
        locked.set()
        assert resume.wait(timeout=10)
        return original(service, identifier)

    monkeypatch.setattr(
        LoadPlanReferenceService, "get_loading_items", pause_after_parent_lock
    )

    def create():
        with s.factory() as db:
            return LoadingService(db).create_session(plan_id)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(create)
        try:
            assert locked.wait(timeout=10)
            # DELETE already holds a child tuple lock when BEFORE ROW runs.
            # Waiting for the parent here would deadlock loading's checklist FK.
            with s.factory() as db:
                with pytest.raises(IntegrityError) as error:
                    db.execute(
                        delete(LoadPlanItem).where(LoadPlanItem.id == min(item_ids))
                    )
                assert (
                    error.value.orig.diag.constraint_name
                    == "ck_load_plans__operational_snapshot"
                )
                db.rollback()
        finally:
            resume.set()
        loading = future.result(timeout=20)
    assert {item.load_plan_item_id for item in loading.items} == item_ids
    with s.factory() as db:
        assert (
            set(
                db.scalars(
                    select(LoadPlanItem.id).where(LoadPlanItem.load_plan_id == plan_id)
                )
            )
            == item_ids
        )


def test_loading_refreshes_cached_snapshot_after_preoperational_mutation(
    distribution_scenario, monkeypatch
):
    s = distribution_scenario
    result = s.create()
    approved = s.post(f"/{result['id']}/approve").json()
    plan_id = uuid.UUID(approved["parts"][0]["load_plan"]["id"])
    cached, enter_lock = Event(), Event()
    original = LoadPlanReferenceService.get_operational_plan
    original_items = LoadPlanReferenceService.get_loading_items
    observed = []
    observed_sequences = []

    def observe(service, identifier, *, for_update=False):
        if for_update:
            enter_lock.set()
        plan = original(service, identifier, for_update=for_update)
        observed.append(plan.truck_id)
        return plan

    monkeypatch.setattr(LoadPlanReferenceService, "get_operational_plan", observe)

    def observe_items(service, identifier):
        items = original_items(service, identifier)
        observed_sequences.extend(item.loading_sequence for item in items)
        return items

    monkeypatch.setattr(LoadPlanReferenceService, "get_loading_items", observe_items)

    def create():
        with s.factory() as db:
            # Keep strong references: reproduce an identity map cached before
            # the concurrent snapshot write commits.
            stale = db.get(LoadPlan, plan_id)
            stale_items = list(stale.items)
            assert stale_items
            cached.set()
            assert changed.wait(timeout=10)
            return LoadingService(db).create_session(plan_id)

    changed = Event()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(create)
        assert cached.wait(timeout=10)
        with s.factory() as db:
            new_truck_id = s.truck_ids[2]
            db.execute(
                update(LoadPlan)
                .where(LoadPlan.id == plan_id)
                .values(truck_id=new_truck_id)
            )
            db.execute(
                update(LoadPlanItem)
                .where(LoadPlanItem.load_plan_id == plan_id)
                .values(loading_sequence=LoadPlanItem.loading_sequence + 1000)
            )
            changed.set()
            assert enter_lock.wait(timeout=10)
            db.commit()
        loading = future.result(timeout=20)
    assert loading.load_plan_id == plan_id
    assert observed == [new_truck_id]
    assert observed_sequences and all(value > 1000 for value in observed_sequences)
