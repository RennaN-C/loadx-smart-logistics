"""OC94 transaction invariants on real PostgreSQL 16."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.deliveries.cancellation_service import TripCancellation
from app.modules.deliveries.models import Delivery, Trip
from app.modules.load_planning.models import LoadPlan
from app.modules.orders.models import Order
from app.modules.status_history.models import StatusHistory
from app.modules.trucks.service import TruckService
from tests.integration.test_deliveries_api import (
    create_trip,
    seed_operational_scenario,
)

SessionFactory = Callable[[], Session]


def _cancel(
    client: TestClient,
    trip_id: str,
    headers: dict[str, str],
    *,
    key: str | None = None,
    reason: str = "Reprogramacao operacional validada",
):
    return client.post(
        f"/api/v1/trips/{trip_id}/cancellation",
        json={"reason": reason, "idempotency_key": key or str(uuid.uuid4())},
        headers=headers,
    )


def test_cancel_scheduled_trip_releases_resources_preserving_audit(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    key = str(uuid.uuid4())
    created = _cancel(
        client, trip["id"], scenario.manager_headers, key=key
    )
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "CANCELED"
    assert created.json()["idempotency_key"] == key

    replay = _cancel(
        client, trip["id"], scenario.manager_headers, key=key
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == created.json()["id"]

    assert _cancel(client, trip["id"], scenario.manager_headers).status_code == 409
    assert _cancel(
        client, trip["id"], scenario.manager_headers,
        key=key, reason="Motivo incompatível com a primeira solicitação",
    ).status_code == 409

    persisted = client.get(
        f"/api/v1/trips/{trip['id']}",
        headers=scenario.manager_headers,
    )
    assert persisted.status_code == 200
    assert persisted.json()["status"] == "CANCELED"
    assert all(
        delivery["status"] == "CANCELED"
        for delivery in persisted.json()["deliveries"]
    )

    with session_factory() as db:
        plan = db.get(LoadPlan, scenario.load_plan_id)
        assert plan is not None and plan.status == "CANCELED"
        assert plan.approved_at is not None
        assert db.scalars(select(Order)).all()
        assert {o.status for o in db.scalars(select(Order)).all()} == {"READY"}
        assert db.scalar(select(func.count()).select_from(TripCancellation)) == 1
        assert db.scalar(
            select(func.count()).select_from(StatusHistory).where(
                StatusHistory.entity_type == "TRIP",
                StatusHistory.entity_id == uuid.UUID(trip["id"]),
                StatusHistory.new_status == "CANCELED",
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(Delivery).where(
                Delivery.trip_id == uuid.UUID(trip["id"]),
                Delivery.status == "DELIVERED",
            )
        ) == 0
        assert not TruckService(db).has_operation_conflict(plan.truck_id)

    # A different approved plan can be created for these READY orders.
    assert client.get(
        f"/api/v1/trips/{trip['id']}/cancellation-preflight",
        headers=scenario.manager_headers,
    ).json()["safe_for_cancellation_workflow"] is False


def test_cancellation_blocked_for_loading_and_restricted_roles(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    path = f"/api/v1/trips/{trip['id']}/cancellation"
    payload = {
        "reason": "Reprogramacao operacional",
        "idempotency_key": str(uuid.uuid4()),
    }
    assert client.post(path, json=payload).status_code == 401
    assert client.post(
        path, json=payload, headers=scenario.driver_headers
    ).status_code == 403
    assert client.post(
        path, json=payload, headers=scenario.checker_headers
    ).status_code == 403
    assert client.post(
        path, json={"reason": "curto", "idempotency_key": str(uuid.uuid4())},
        headers=scenario.manager_headers,
    ).status_code == 422

    loading = client.post(
        "/api/v1/loading-sessions",
        json={"load_plan_id": str(scenario.load_plan_id)},
        headers=scenario.manager_headers,
    )
    assert loading.status_code == 201
    blocked = client.post(
        path, json=payload, headers=scenario.manager_headers
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "TRIP_CANCELLATION_BLOCKED"
    with session_factory() as db:
        assert db.get(Trip, uuid.UUID(trip["id"])).status == "SCHEDULED"
        assert db.scalar(select(func.count()).select_from(TripCancellation)) == 0


def test_cancellation_is_transactional_on_history_failure(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)

    from app.modules.deliveries.cancellation_service import TripCancellationService

    def broken_history(*_args, **_kwargs):
        raise RuntimeError("simulated history write failure")

    monkeypatch.setattr(TripCancellationService, "_history", broken_history)
    try:
        _cancel(client, trip["id"], scenario.manager_headers)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Injected failure must propagate")

    with session_factory() as db:
        assert db.get(Trip, uuid.UUID(trip["id"])).status == "SCHEDULED"
        assert db.get(LoadPlan, scenario.load_plan_id).status == "APPROVED"
        assert {o.status for o in db.scalars(select(Order)).all()} == {"PLANNED"}
        assert db.scalar(select(func.count()).select_from(TripCancellation)) == 0
