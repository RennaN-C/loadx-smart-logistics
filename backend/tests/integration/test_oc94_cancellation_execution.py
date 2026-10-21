"""OC94 transaction invariants on real PostgreSQL 16."""

import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.deliveries.cancellation_service import TripCancellation
from app.modules.deliveries.models import Delivery, Trip
from app.modules.load_planning.distribution_models import LoadDistributionVolume
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
    created = _cancel(client, trip["id"], scenario.manager_headers, key=key)
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "CANCELED"
    assert created.json()["idempotency_key"] == key

    replay = _cancel(client, trip["id"], scenario.manager_headers, key=key)
    assert replay.status_code == 200
    assert replay.json()["id"] == created.json()["id"]

    assert _cancel(client, trip["id"], scenario.manager_headers).status_code == 409
    assert (
        _cancel(
            client,
            trip["id"],
            scenario.manager_headers,
            key=key,
            reason="Motivo incompatível com a primeira solicitação",
        ).status_code
        == 409
    )

    persisted = client.get(
        f"/api/v1/trips/{trip['id']}",
        headers=scenario.manager_headers,
    )
    assert persisted.status_code == 200
    assert persisted.json()["status"] == "CANCELED"
    assert all(
        delivery["status"] == "CANCELED" for delivery in persisted.json()["deliveries"]
    )

    with session_factory() as db:
        plan = db.get(LoadPlan, scenario.load_plan_id)
        assert plan is not None and plan.status == "CANCELED"
        assert plan.approved_at is not None
        assert db.scalars(select(Order)).all()
        assert {o.status for o in db.scalars(select(Order)).all()} == {"READY"}
        assert db.scalar(select(func.count()).select_from(TripCancellation)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(StatusHistory)
                .where(
                    StatusHistory.entity_type == "TRIP",
                    StatusHistory.entity_id == uuid.UUID(trip["id"]),
                    StatusHistory.new_status == "CANCELED",
                )
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Delivery)
                .where(
                    Delivery.trip_id == uuid.UUID(trip["id"]),
                    Delivery.status == "DELIVERED",
                )
            )
            == 0
        )
        assert not TruckService(db).has_operation_conflict(plan.truck_id)

    # A different approved plan can be created for these READY orders.
    assert (
        client.get(
            f"/api/v1/trips/{trip['id']}/cancellation-preflight",
            headers=scenario.manager_headers,
        ).json()["safe_for_cancellation_workflow"]
        is False
    )


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
    assert (
        client.post(path, json=payload, headers=scenario.driver_headers).status_code
        == 403
    )
    assert (
        client.post(path, json=payload, headers=scenario.checker_headers).status_code
        == 403
    )
    assert (
        client.post(
            path,
            json={"reason": "curto", "idempotency_key": str(uuid.uuid4())},
            headers=scenario.manager_headers,
        ).status_code
        == 422
    )

    loading = client.post(
        "/api/v1/loading-sessions",
        json={"load_plan_id": str(scenario.load_plan_id)},
        headers=scenario.manager_headers,
    )
    assert loading.status_code == 201
    blocked = client.post(path, json=payload, headers=scenario.manager_headers)
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


def test_cancel_one_part_preserves_sibling_trip_and_allows_reprocess(
    client: TestClient, session_factory: SessionFactory
) -> None:
    from tests.integration.oc90_helpers import seed_multi_flow

    s = seed_multi_flow(client, session_factory)
    s.approve()
    s.trips = [s.create_trip(0), s.create_trip(1)]
    original_part = s.parts[0]
    sibling_trip = s.trips[1]

    # Only the sibling is loaded and on the road: aggregate order is IN_TRANSIT.
    s.loadings = [None, s.create_loading(1)]
    s.finish_loading(1)
    s.trip_status(1, "IN_ROUTE")
    assert s.status() == "IN_TRANSIT"

    canceled = _cancel(
        client,
        s.trips[0]["id"],
        s.headers,
        reason="Falha na alocacao inicial do primeiro veiculo",
    )
    assert canceled.status_code == 200, canceled.text
    after = s.request("GET", f"/load-distributions/{s.distribution['id']}")
    assert after["status"] == "INCOMPLETE"
    assert sum(1 for part in after["parts"] if part["status"] == "CANCELED") == 1
    with session_factory() as db:
        physical = db.scalars(
            select(LoadDistributionVolume).where(
                LoadDistributionVolume.distribution_id == uuid.UUID(after["id"])
            )
        ).all()
        assert physical and all(volume.active for volume in physical)
    assert s.status() == "IN_TRANSIT"
    assert s.request("GET", f"/trips/{sibling_trip['id']}")["status"] == "IN_ROUTE"

    response = s.request(
        "POST",
        f"/load-distributions/{after['id']}/parts/{original_part['id']}/reprocess",
        {
            "truck_id": original_part["load_plan"]["truck_id"],
            "expected_load_plan_id": original_part["load_plan"]["id"],
        },
    )
    replacement = next(
        part for part in response["parts"] if part["id"] == original_part["id"]
    )
    assert replacement["load_plan"]["id"] != original_part["load_plan"]["id"]
    approved = s.request("POST", f"/load-distributions/{after['id']}/approve", {})
    assert approved["status"] == "APPROVED"
    assert s.status() == "IN_TRANSIT"
    new_trip = s.request(
        "POST",
        "/trips",
        {
            "load_plan_id": replacement["load_plan"]["id"],
            "driver_id": s.drivers[0]["id"],
        },
        expected=201,
    )
    assert new_trip["status"] == "SCHEDULED"
    assert s.request("GET", f"/trips/{sibling_trip['id']}")["status"] == "IN_ROUTE"


def test_oc94_concurrent_cancel_commands_are_idempotent(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    path = f"/api/v1/trips/{trip['id']}/cancellation"
    key = str(uuid.uuid4())
    barrier = Barrier(2)

    def request(_: int):
        barrier.wait(timeout=10)
        return client.post(
            path,
            headers=scenario.manager_headers,
            json={"reason": "Cancelamento simultaneo validado", "idempotency_key": key},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        replies = list(executor.map(request, range(2)))
    assert [reply.status_code for reply in replies] == [200, 200], [
        reply.text for reply in replies
    ]
    assert replies[0].json()["id"] == replies[1].json()["id"]
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(TripCancellation)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(StatusHistory)
                .where(
                    StatusHistory.entity_type == "TRIP",
                    StatusHistory.entity_id == uuid.UUID(trip["id"]),
                    StatusHistory.new_status == "CANCELED",
                )
            )
            == 1
        )


def test_oc94_concurrent_different_keys_have_one_winner(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    path = f"/api/v1/trips/{trip['id']}/cancellation"
    barrier = Barrier(2)

    def request(_: int):
        barrier.wait(timeout=10)
        return client.post(
            path,
            headers=scenario.manager_headers,
            json={
                "reason": "Cancelamento concorrente com mesma viagem",
                "idempotency_key": str(uuid.uuid4()),
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        replies = list(executor.map(request, range(2)))
    assert sorted(reply.status_code for reply in replies) == [200, 409], [
        reply.text for reply in replies
    ]
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(TripCancellation)) == 1
