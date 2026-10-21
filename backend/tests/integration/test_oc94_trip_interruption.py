"""OC94: PostgreSQL transaction checks for trip interruption/resumption."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.deliveries.interruption_service import TripInterruptionEvent
from app.modules.deliveries.models import Trip
from app.modules.drivers.service import DriverService
from app.modules.load_planning.models import LoadPlan
from app.modules.orders.models import Order
from app.modules.status_history.models import StatusHistory
from app.modules.trucks.service import TruckService
from tests.integration.test_oc94_exception_lifecycle import _in_route

SessionFactory = Callable[[], Session]


def _command(client, trip_id, action, headers, key=None):
    return client.post(
        f"/api/v1/trips/{trip_id}/{action}",
        headers=headers,
        json={
            "reason": "Ocorrencia documentada pela central logistica",
            "idempotency_key": key or str(uuid.uuid4()),
        },
    )


def test_interrupt_and_resume_preserve_resources_and_original_start(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario, delivery = _in_route(client, session_factory, monkeypatch)
    trip_id = delivery["trip_id"]
    url = f"/api/v1/trips/{trip_id}/interruptions"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=scenario.driver_headers).status_code == 403
    assert (
        _command(client, trip_id, "interruptions", scenario.driver_headers).status_code
        == 403
    )
    with session_factory() as db:
        trip_before = db.get(Trip, uuid.UUID(trip_id))
        started_at = trip_before.started_at

    key = str(uuid.uuid4())
    first = _command(client, trip_id, "interruptions", scenario.manager_headers, key)
    assert first.status_code == 200, first.text
    assert first.json()["action"] == "INTERRUPTED"
    replay = _command(client, trip_id, "interruptions", scenario.manager_headers, key)
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    assert (
        _command(client, trip_id, "interruptions", scenario.manager_headers).status_code
        == 409
    )

    unavailable_delivery = client.patch(
        f"/api/v1/deliveries/{delivery['id']}/status",
        json={"status": "IN_DELIVERY"},
        headers=scenario.driver_headers,
    )
    assert unavailable_delivery.status_code == 409
    with session_factory() as db:
        paused = db.get(Trip, uuid.UUID(trip_id))
        plan = db.get(LoadPlan, paused.load_plan_id)
        assert paused.status == "INTERRUPTED"
        assert paused.started_at == started_at
        assert paused.finished_at is None
        assert plan.status == "APPROVED"
        assert TruckService(db).has_operation_conflict(plan.truck_id)
        assert DriverService(db).has_operation_conflict(paused.driver_id)
        assert {order.status for order in db.scalars(select(Order)).all()} == {
            "IN_TRANSIT"
        }

    resumed = _command(client, trip_id, "resumptions", scenario.manager_headers)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["trip_status"] == "IN_ROUTE"
    with session_factory() as db:
        trip_after = db.get(Trip, uuid.UUID(trip_id))
        assert trip_after.started_at == started_at
        assert (
            db.scalar(
                select(func.count())
                .select_from(StatusHistory)
                .where(
                    StatusHistory.entity_type == "TRIP",
                    StatusHistory.entity_id == trip_after.id,
                    StatusHistory.new_status == "IN_ROUTE",
                )
            )
            == 2
        )
        assert db.scalar(select(func.count()).select_from(TripInterruptionEvent)) == 2

    history = client.get(url, headers=scenario.manager_headers)
    assert history.status_code == 200
    assert [e["action"] for e in history.json()] == ["INTERRUPTED", "RESUMED"]


def test_interruption_failure_rolls_back_trip_and_ledger(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario, delivery = _in_route(client, session_factory, monkeypatch)
    from app.modules.status_history.service import StatusHistoryService

    def fail(*_args, **_kwargs):
        raise RuntimeError("Injected audit failure")

    with monkeypatch.context() as patch:
        patch.setattr(StatusHistoryService, "stage_status_change", fail)
        response = _command(
            client, delivery["trip_id"], "interruptions", scenario.manager_headers
        )
        assert response.status_code == 500

    with session_factory() as db:
        assert db.get(Trip, uuid.UUID(delivery["trip_id"])).status == "IN_ROUTE"
        assert db.scalar(select(func.count()).select_from(TripInterruptionEvent)) == 0
