import uuid

from fastapi.testclient import TestClient

from app.modules.users.models import User
from tests.integration.auth_helpers import issue_session_headers


def test_complete_v1_flow(client: TestClient, session_factory) -> None:
    with session_factory() as db:
        manager = User(
            name="Gestor E2E",
            email=f"manager-e2e-{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="LOGISTICS_MANAGER",
            active=True,
        )
        db.add(manager)
        db.commit()
        manager_id = manager.id
    manager_headers = issue_session_headers(session_factory, manager_id)

    customer = client.post(
        "/api/v1/customers",
        json={
            "name": "Cliente E2E",
            "document": uuid.uuid4().hex,
            "phone": "551100000001",
            "address": "Rua E2E, 100",
            "city": "Sao Paulo",
            "state": "SP",
        },
        headers=manager_headers,
    ).json()
    driver = client.post(
        "/api/v1/drivers",
        json={
            "name": "Motorista E2E",
            "document": f"DOC-{uuid.uuid4().hex[:20]}",
            "phone": "551100000002",
            "license_number": f"CNH-{uuid.uuid4().hex[:20]}",
            "license_category": "D",
        },
        headers=manager_headers,
    ).json()
    truck = client.post(
        "/api/v1/trucks",
        json={
            "plate": f"E{uuid.uuid4().hex[:6]}",
            "model": "Bau E2E",
            "internal_width_cm": 100,
            "internal_height_cm": 100,
            "internal_length_cm": 100,
            "max_weight_kg": 1000.0,
        },
        headers=manager_headers,
    ).json()
    product = client.post(
        "/api/v1/products",
        json={
            "code": f"E2E-{uuid.uuid4().hex[:8]}",
            "name": "Caixa E2E",
            "width_cm": 10,
            "height_cm": 10,
            "length_cm": 10,
            "weight_kg": 1.0,
            "fragile": False,
            "stackable": True,
            "rotation_allowed": True,
        },
        headers=manager_headers,
    ).json()

    with session_factory() as db:
        driver_user = User(
            name="Usuario Motorista E2E",
            email=f"driver-e2e-{uuid.uuid4().hex}@example.test",
            password_hash="hash-ficticio",
            role="DRIVER",
            driver_id=uuid.UUID(driver["id"]),
            active=True,
        )
        db.add(driver_user)
        db.commit()

    order_response = client.post(
        "/api/v1/orders",
        json={
            "customer_id": customer["id"],
            "priority": "NORMAL",
            "delivery_address": "Rua E2E, 200",
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 1,
                    "delivery_sequence": 1,
                }
            ],
        },
        headers=manager_headers,
    )
    assert order_response.status_code == 201
    order = order_response.json()
    ready = client.patch(
        f"/api/v1/orders/{order['id']}/status",
        json={"status": "READY"},
        headers=manager_headers,
    )
    assert ready.status_code == 200

    plan_response = client.post(
        "/api/v1/load-plans",
        json={"truck_id": truck["id"], "order_ids": [order["id"]]},
        headers=manager_headers,
    )
    assert plan_response.status_code == 201
    plan = plan_response.json()
    approved = client.post(
        f"/api/v1/load-plans/{plan['id']}/approve", headers=manager_headers
    )
    assert approved.status_code == 200

    loading = client.post(
        "/api/v1/loading-sessions",
        json={"load_plan_id": plan["id"]},
        headers=manager_headers,
    ).json()
    client.patch(
        f"/api/v1/loading-sessions/{loading['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=manager_headers,
    )
    for item in loading["items"]:
        client.patch(
            f"/api/v1/loading-sessions/{loading['id']}/items/{item['id']}",
            json={"status": "CHECKED"},
            headers=manager_headers,
        )
    finished_loading = client.patch(
        f"/api/v1/loading-sessions/{loading['id']}/status",
        json={"status": "FINISHED"},
        headers=manager_headers,
    )
    assert finished_loading.status_code == 200

    trip_response = client.post(
        "/api/v1/trips",
        json={"load_plan_id": plan["id"], "driver_id": driver["id"]},
        headers=manager_headers,
    )
    assert trip_response.status_code == 201
    trip = trip_response.json()
    for command in ("INICIAR VIAGEM", "INICIAR ENTREGA", "FINALIZAR ENTREGA"):
        executed = client.post(
            "/api/v1/messages/interpret",
            json={"driver_phone": driver["phone"], "message": command},
        )
        assert executed.status_code == 200
        assert executed.json()["executed"] is True

    finished_trip = client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        json={"status": "FINISHED"},
        headers=manager_headers,
    )
    assert finished_trip.status_code == 200

    occurrence = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": trip["id"],
            "delivery_id": trip["deliveries"][0]["id"],
            "type": "DELAY",
            "description": "Ocorrência controlada E2E.",
            "photo_url": "mock://occurrences/e2e-photo",
        },
        headers=manager_headers,
    )
    assert occurrence.status_code == 201

    for path in (
        f"/api/v1/reports/load-plans/{plan['id']}",
        f"/api/v1/reports/trips/{trip['id']}",
    ):
        report = client.get(path, headers=manager_headers)
        assert report.status_code == 200
        assert report.headers["content-type"] == "application/pdf"
        assert report.content.startswith(b"%PDF-")
