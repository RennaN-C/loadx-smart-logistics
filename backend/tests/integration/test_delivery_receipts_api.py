import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.service import TripService
from app.modules.drivers.models import Driver
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.orders.models import Order
from app.modules.status_history.models import StatusHistory
from tests.integration.test_deliveries_api import (
    SessionFactory,
    create_trip,
    create_unlinked_driver_headers,
    seed_operational_scenario,
)


def prepare_delivery(client, session_factory, monkeypatch):
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    monkeypatch.setattr(
        LoadingReferenceService, "is_load_plan_finished", lambda _self, _plan_id: True
    )
    started = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "IN_ROUTE"},
        headers=scenario.driver_headers,
    )
    assert started.status_code == 200
    delivery = trip["deliveries"][0]
    response = client.patch(
        f"/api/v1/deliveries/{delivery['id']}/status",
        json={"status": "IN_DELIVERY"},
        headers=scenario.driver_headers,
    )
    assert response.status_code == 200
    return scenario, trip, delivery, f"/api/v1/deliveries/{delivery['id']}/receipt"


@pytest.mark.parametrize("operator", ("driver", "manager"))
def test_receipt_registration_tracks_exact_delivery_and_is_idempotent(
    client: TestClient, session_factory: SessionFactory, monkeypatch, operator: str
) -> None:
    scenario, trip, delivery, path = prepare_delivery(
        client, session_factory, monkeypatch
    )
    headers = getattr(scenario, f"{operator}_headers")
    with session_factory() as db:
        history_count = len(db.scalars(select(StatusHistory)).all())
    response = client.post(path, json={}, headers=headers)
    assert response.status_code == 200
    receipt = response.json()
    assert set(receipt) == {
        "id",
        "delivery_id",
        "trip_id",
        "order_id",
        "driver_id",
        "delivered_at",
        "recorded_at",
        "recorded_by",
    }
    assert receipt["delivery_id"] == delivery["id"]
    assert receipt["trip_id"] == trip["id"]
    assert receipt["order_id"] == delivery["order_id"]
    assert receipt["driver_id"] == str(scenario.driver_id)
    assert (
        datetime.fromisoformat(receipt["delivered_at"]).utcoffset().total_seconds() == 0
    )
    assert (
        datetime.fromisoformat(receipt["recorded_at"]).utcoffset().total_seconds() == 0
    )
    # Retrying with a different authorized user preserves original attribution.
    for retry_headers in (scenario.manager_headers, scenario.driver_headers):
        repeated = client.post(path, json={}, headers=retry_headers)
        assert repeated.status_code == 200
        assert repeated.json() == receipt
    for reader_headers in (
        scenario.admin_headers,
        scenario.manager_headers,
        scenario.driver_headers,
    ):
        queried = client.get(path, headers=reader_headers)
        assert queried.status_code == 200
        assert queried.json() == receipt
    with session_factory() as db:
        history = db.get(StatusHistory, uuid.UUID(receipt["id"]))
        assert history.entity_type == "DELIVERY"
        assert history.entity_id == uuid.UUID(delivery["id"])
        assert str(history.changed_by) == receipt["recorded_by"]
        assert history.old_status == "IN_DELIVERY"
        assert history.new_status == "DELIVERED"
        assert len(db.scalars(select(StatusHistory)).all()) == history_count + 2
        assert db.get(Delivery, uuid.UUID(delivery["id"])).status == "DELIVERED"
        assert db.get(Order, uuid.UUID(delivery["order_id"])).status == "DELIVERED"
        other = trip["deliveries"][1]
        assert db.get(Delivery, uuid.UUID(other["id"])).status == "PENDING"
        assert db.get(Order, uuid.UUID(other["order_id"])).status == "IN_TRANSIT"
    other_receipt = client.get(
        f"/api/v1/deliveries/{trip['deliveries'][1]['id']}/receipt",
        headers=scenario.manager_headers,
    )
    assert other_receipt.status_code == 409


def test_receipt_preserves_existing_status_contract_and_finished_trip_flow(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario, trip, delivery, path = prepare_delivery(
        client, session_factory, monkeypatch
    )
    response = client.patch(
        f"/api/v1/deliveries/{delivery['id']}/status",
        json={"status": "DELIVERED"},
        headers=scenario.driver_headers,
    )
    assert response.status_code == 200
    assert set(response.json()) == {
        "id",
        "trip_id",
        "order_id",
        "status",
        "sequence",
        "delivered_at",
    }
    receipt = client.get(path, headers=scenario.admin_headers).json()
    assert receipt["delivered_at"] == response.json()["delivered_at"]
    for other in trip["deliveries"][1:]:
        assert (
            client.patch(
                f"/api/v1/deliveries/{other['id']}/status",
                json={"status": "IN_DELIVERY"},
                headers=scenario.driver_headers,
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/deliveries/{other['id']}/receipt",
                json={},
                headers=scenario.driver_headers,
            ).status_code
            == 200
        )
    finished = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "FINISHED"},
        headers=scenario.driver_headers,
    )
    assert finished.status_code == 200
    assert client.post(path, json={}, headers=scenario.driver_headers).json() == receipt
    assert client.get(path, headers=scenario.admin_headers).json() == receipt


def test_receipt_rejects_nonexistent_delivery_and_nonpermitted_states(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    path = f"/api/v1/deliveries/{trip['deliveries'][0]['id']}/receipt"
    missing_path = f"/api/v1/deliveries/{uuid.uuid4()}/receipt"
    for method in ("GET", "POST"):
        options = {"json": {}} if method == "POST" else {}
        missing = client.request(
            method, missing_path, headers=scenario.manager_headers, **options
        )
        assert missing.status_code == 404
        assert missing.json()["code"] == "DELIVERY_NOT_FOUND"
    pending = client.post(path, json={}, headers=scenario.manager_headers)
    assert pending.status_code == 409
    assert pending.json()["code"] == "DELIVERY_STATUS_TRANSITION_NOT_ALLOWED"
    unavailable = client.get(path, headers=scenario.manager_headers)
    assert unavailable.status_code == 409
    assert unavailable.json()["code"] == "DELIVERY_RECEIPT_NOT_AVAILABLE"
    # Legacy inconsistent operational state still cannot bypass the in-route gate.
    with session_factory() as db:
        db.get(Delivery, uuid.UUID(trip["deliveries"][0]["id"])).status = "IN_DELIVERY"
        db.commit()
    outside_route = client.post(path, json={}, headers=scenario.manager_headers)
    assert outside_route.status_code == 409
    assert outside_route.json()["code"] == "DELIVERY_TRIP_NOT_IN_ROUTE"


def test_receipt_enforces_roles_ownership_authentication_and_csrf(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario, _trip, _delivery, path = prepare_delivery(
        client, session_factory, monkeypatch
    )
    unlinked = create_unlinked_driver_headers(session_factory)
    for headers in (scenario.checker_headers, scenario.other_driver_headers, unlinked):
        for method in ("GET", "POST"):
            options = {"json": {}} if method == "POST" else {}
            denied = client.request(method, path, headers=headers, **options)
            assert denied.status_code == 403
            assert denied.json()["code"] == "AUTH_FORBIDDEN"
    assert client.post(path, json={}, headers=scenario.admin_headers).status_code == 403
    assert client.get(path).status_code == 401
    assert client.post(path, json={}).status_code == 401
    csrf_headers = {
        key: value
        for key, value in scenario.driver_headers.items()
        if key.lower() != "x-csrf-token"
    }
    no_csrf = client.post(path, json={}, headers=csrf_headers)
    assert no_csrf.status_code == 403
    assert no_csrf.json()["code"] == "AUTH_CSRF_INVALID"
    bad_origin = client.post(
        path,
        json={},
        headers=scenario.driver_headers | {"Origin": "https://invalid.example.test"},
    )
    assert bad_origin.status_code == 403
    assert bad_origin.json()["code"] == "AUTH_ORIGIN_FORBIDDEN"
    with session_factory() as db:
        db.get(Driver, scenario.driver_id).active = False
        db.commit()
    for method in ("GET", "POST"):
        options = {"json": {}} if method == "POST" else {}
        assert (
            client.request(
                method, path, headers=scenario.driver_headers, **options
            ).status_code
            == 403
        )


@pytest.mark.parametrize(
    "field",
    (
        "delivery_id",
        "trip_id",
        "order_id",
        "recorded_by",
        "delivered_at",
        "recipient_name",
        "photo_url",
        "signature",
        "latitude",
    ),
)
def test_receipt_rejects_client_supplied_facts_and_unimplemented_evidence(
    client: TestClient, session_factory: SessionFactory, monkeypatch, field: str
) -> None:
    scenario, _trip, delivery, path = prepare_delivery(
        client, session_factory, monkeypatch
    )
    response = client.post(
        path, json={field: "forged-value"}, headers=scenario.driver_headers
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    with session_factory() as db:
        assert db.get(Delivery, uuid.UUID(delivery["id"])).status == "IN_DELIVERY"


def test_receipt_requires_body_and_valid_uuid_and_documents_openapi(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario, _trip, _delivery, path = prepare_delivery(
        client, session_factory, monkeypatch
    )
    assert client.post(path, headers=scenario.driver_headers).status_code == 422
    assert (
        client.post(
            "/api/v1/deliveries/invalid/receipt",
            json={},
            headers=scenario.driver_headers,
        ).status_code
        == 422
    )
    spec = client.get("/openapi.json").json()
    for method in ("get", "post"):
        operation = spec["paths"]["/api/v1/deliveries/{delivery_id}/receipt"][method]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("DeliveryReceiptRead")
        assert operation["security"] == [{"SessionCookie": []}]
    create_schema = spec["components"]["schemas"]["DeliveryReceiptCreate"]
    assert create_schema["additionalProperties"] is False
    assert create_schema["properties"] == {}


@pytest.mark.parametrize("invalid_history", ("missing", "unattributed", "duplicate"))
def test_receipt_never_fabricates_incomplete_legacy_completion(
    client: TestClient,
    session_factory: SessionFactory,
    monkeypatch,
    invalid_history: str,
) -> None:
    scenario, _trip, _delivery, path = prepare_delivery(
        client, session_factory, monkeypatch
    )
    receipt = client.post(path, json={}, headers=scenario.driver_headers).json()
    with session_factory() as db:
        history = db.get(StatusHistory, uuid.UUID(receipt["id"]))
        if invalid_history == "missing":
            db.delete(history)
        elif invalid_history == "unattributed":
            history.changed_by = None
        else:
            db.add(
                StatusHistory(
                    entity_type="DELIVERY",
                    entity_id=history.entity_id,
                    old_status="IN_DELIVERY",
                    new_status="DELIVERED",
                    changed_by=history.changed_by,
                )
            )
        db.commit()
    for method in ("GET", "POST"):
        options = {"json": {}} if method == "POST" else {}
        response = client.request(
            method, path, headers=scenario.manager_headers, **options
        )
        assert response.status_code == 409
        assert response.json()["code"] == "DELIVERY_RECEIPT_HISTORY_INVALID"


def test_receipt_projection_failure_rolls_back_atomic_completion(
    client: TestClient, session_factory: SessionFactory, monkeypatch
) -> None:
    scenario, trip, delivery, path = prepare_delivery(
        client, session_factory, monkeypatch
    )
    with session_factory() as db:
        history_count = len(db.scalars(select(StatusHistory)).all())

    def fail(*_args, **_kwargs):
        raise RuntimeError("falha ficticia de projecao")

    monkeypatch.setattr(TripService, "_build_delivery_receipt", fail)
    response = client.post(path, json={}, headers=scenario.driver_headers)
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"
    with session_factory() as db:
        persisted = db.get(Delivery, uuid.UUID(delivery["id"]))
        assert persisted.status == "IN_DELIVERY"
        assert persisted.delivered_at is None
        assert db.get(Order, persisted.order_id).status == "IN_TRANSIT"
        assert db.get(Trip, uuid.UUID(trip["id"])).status == "IN_ROUTE"
        assert len(db.scalars(select(StatusHistory)).all()) == history_count
