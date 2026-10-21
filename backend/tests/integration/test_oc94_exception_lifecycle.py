"""OC94: PostgreSQL-backed exception lifecycle, authorization and replay."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.deliveries.exception_models import DeliveryException
from app.modules.loading.reference_service import LoadingReferenceService
from tests.integration.test_deliveries_api import (
    create_trip,
    seed_operational_scenario,
)

SessionFactory = Callable[[], Session]


def _in_route(client: TestClient, session_factory: SessionFactory, monkeypatch):
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    monkeypatch.setattr(
        LoadingReferenceService,
        "is_load_plan_finished",
        lambda _self, _load_plan_id: True,
    )
    start = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=scenario.manager_headers,
    )
    assert start.status_code == 200
    return scenario, start.json()["deliveries"][0]


def _record(
    client: TestClient,
    delivery_id: str,
    headers: dict[str, str],
    code: str,
    *,
    key: str | None = None,
    reason: str = "Cliente nao localizado no endereco informado",
    scheduled_for: str | None = None,
):
    payload = {
        "code": code,
        "reason": reason,
        "idempotency_key": key or str(uuid.uuid4()),
    }
    if scheduled_for is not None:
        payload["scheduled_for"] = scheduled_for
    return client.post(
        f"/api/v1/deliveries/{delivery_id}/exceptions",
        json=payload,
        headers=headers,
    )


def test_oc94_replay_permissions_and_receipt_gate(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario, delivery = _in_route(client, session_factory, monkeypatch)
    path = f"/api/v1/deliveries/{delivery['id']}/exceptions"

    assert client.get(path).status_code == 401
    assert client.get(path, headers=scenario.checker_headers).status_code == 403
    assert (
        client.get(path, headers=scenario.other_driver_headers).status_code == 403
    )

    key = str(uuid.uuid4())
    first = _record(
        client,
        delivery["id"],
        scenario.driver_headers,
        "CUSTOMER_ABSENT",
        key=key,
    )
    assert first.status_code == 201
    assert first.json()["code"] == "CUSTOMER_ABSENT"
    assert first.json()["delivery_id"] == delivery["id"]
    replay = _record(
        client,
        delivery["id"],
        scenario.driver_headers,
        "CUSTOMER_ABSENT",
        key=key,
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]

    mismatch = _record(
        client,
        delivery["id"],
        scenario.driver_headers,
        "REFUSED",
        key=key,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["code"] == "DELIVERY_EXCEPTION_IDEMPOTENCY_CONFLICT"

    duplicate_attempt = _record(
        client, delivery["id"], scenario.driver_headers, "REFUSED"
    )
    assert duplicate_attempt.status_code == 409
    assert duplicate_attempt.json()["code"] == "DELIVERY_EXCEPTION_PENDING"

    advance = client.patch(
        f"/api/v1/deliveries/{delivery['id']}/status",
        json={"status": "IN_DELIVERY"},
        headers=scenario.driver_headers,
    )
    assert advance.status_code == 200
    finish = client.patch(
        f"/api/v1/deliveries/{delivery['id']}/status",
        json={"status": "DELIVERED"},
        headers=scenario.driver_headers,
    )
    assert finish.status_code == 409
    assert finish.json()["code"] == "DELIVERY_EXCEPTION_PENDING"
    assert client.post(
        f"/api/v1/deliveries/{delivery['id']}/receipt",
        json={},
        headers=scenario.driver_headers,
    ).status_code == 409

    events = client.get(path, headers=scenario.manager_headers)
    assert events.status_code == 200
    assert len(events.json()) == 1
    with session_factory() as db:
        stored = db.scalars(
            select(DeliveryException).where(
                DeliveryException.delivery_id == uuid.UUID(delivery["id"])
            )
        ).all()
        assert len(stored) == 1

    resumed = _record(
        client,
        delivery["id"],
        scenario.driver_headers,
        "RESUMED",
        reason="Reabertura autorizada para nova tentativa de entrega",
    )
    assert resumed.status_code == 201
    delivered = client.patch(
        f"/api/v1/deliveries/{delivery['id']}/status",
        json={"status": "DELIVERED"},
        headers=scenario.driver_headers,
    )
    assert delivered.status_code == 200
    assert delivered.json()["delivered_at"] is not None

    # A same-key replay remains idempotent after completion; new actions do not.
    assert _record(
        client, delivery["id"], scenario.driver_headers, "CUSTOMER_ABSENT",
        key=key,
    ).status_code == 200
    assert _record(
        client, delivery["id"], scenario.driver_headers, "DAMAGED"
    ).status_code == 409


def test_oc94_reagendamento_exige_falha_e_respeita_prazo(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario, delivery = _in_route(client, session_factory, monkeypatch)
    headers = scenario.manager_headers
    identifier = delivery["id"]
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()

    premature = _record(
        client, identifier, headers, "RESCHEDULED",
        scheduled_for=future, reason="Entrega reagendada com o destinatario",
    )
    assert premature.status_code == 409
    assert premature.json()["code"] == "DELIVERY_EXCEPTION_TRANSITION_INVALID"
    assert _record(
        client, identifier, headers, "RESUMED",
        reason="Retomada solicitada sem incidente anterior",
    ).status_code == 409

    failure = _record(client, identifier, headers, "REFUSED")
    assert failure.status_code == 201
    schedule = _record(
        client, identifier, headers, "RESCHEDULED", scheduled_for=future,
        reason="Nova data de entrega combinada com destinatario",
    )
    assert schedule.status_code == 201
    early = _record(
        client, identifier, headers, "RESUMED",
        reason="Nova tentativa solicitada antes da data prevista",
    )
    assert early.status_code == 409
    assert early.json()["code"] == "DELIVERY_EXCEPTION_SCHEDULE_PENDING"

    again = _record(client, identifier, headers, "CUSTOMER_ABSENT")
    assert again.status_code == 409
    assert again.json()["code"] == "DELIVERY_EXCEPTION_PENDING"

    read = client.get(
        f"/api/v1/deliveries/{identifier}/exceptions",
        headers=scenario.driver_headers,
    )
    assert read.status_code == 200
    assert [item["code"] for item in read.json()] == ["REFUSED", "RESCHEDULED"]


def test_oc94_out_of_route_is_rejected_without_creating_history(
    client: TestClient, session_factory: SessionFactory
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    delivery_id = trip["deliveries"][0]["id"]
    response = _record(
        client, delivery_id, scenario.manager_headers, "CUSTOMER_ABSENT"
    )
    assert response.status_code == 409
    assert response.json()["code"] == "DELIVERY_EXCEPTION_NOT_ELIGIBLE"
    with session_factory() as db:
        assert db.scalars(select(DeliveryException)).all() == []
