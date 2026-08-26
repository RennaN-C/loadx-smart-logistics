import uuid

from fastapi.testclient import TestClient

from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario


def test_manager_registers_and_lists_trip_occurrences(
    client: TestClient,
    session_factory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    delivery_id = trip["deliveries"][0]["id"]

    created = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": trip["id"],
            "delivery_id": delivery_id,
            "type": "DAMAGED_PRODUCT",
            "description": "Uma caixa foi danificada durante a entrega.",
            "photo_url": "mock://occurrences/photo-1",
        },
        headers=scenario.manager_headers,
    )

    assert created.status_code == 201
    assert created.json()["trip_id"] == trip["id"]
    assert created.json()["delivery_id"] == delivery_id
    assert created.json()["photo_url"] == "mock://occurrences/photo-1"

    without_photo = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": trip["id"],
            "type": "DELAY",
            "description": "Atraso operacional.",
        },
        headers=scenario.manager_headers,
    )
    assert without_photo.status_code == 201
    assert without_photo.json()["photo_url"] is None

    listed = client.get(
        f"/api/v1/trips/{trip['id']}/occurrences",
        headers=scenario.manager_headers,
    )
    assert listed.status_code == 200
    assert {occurrence["id"] for occurrence in listed.json()} == {
        created.json()["id"],
        without_photo.json()["id"],
    }


def test_occurrence_rejects_unknown_trip_and_delivery_references(
    client: TestClient,
    session_factory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    unknown_id = str(uuid.uuid4())

    unknown_trip = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": unknown_id,
            "type": "DELAY",
            "description": "Atraso operacional.",
        },
        headers=scenario.manager_headers,
    )
    unknown_delivery = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": trip["id"],
            "delivery_id": unknown_id,
            "type": "DELAY",
            "description": "Atraso operacional.",
        },
        headers=scenario.manager_headers,
    )

    assert unknown_trip.status_code == 404
    assert unknown_trip.json()["code"] == "TRIP_NOT_FOUND"
    assert unknown_delivery.status_code == 404
    assert unknown_delivery.json()["code"] == "DELIVERY_NOT_FOUND"


def test_occurrence_rejects_delivery_from_another_trip(
    client: TestClient,
    session_factory,
) -> None:
    first_scenario = seed_operational_scenario(session_factory)
    second_scenario = seed_operational_scenario(session_factory)
    first_trip = create_trip(client, first_scenario)
    second_trip = create_trip(client, second_scenario)

    response = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": first_trip["id"],
            "delivery_id": second_trip["deliveries"][0]["id"],
            "type": "WRONG_ADDRESS",
            "description": "Endereço incompatível.",
        },
        headers=first_scenario.manager_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "OCCURRENCE_DELIVERY_TRIP_MISMATCH"


def test_occurrence_rejects_unknown_type(
    client: TestClient,
    session_factory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)

    response = client.post(
        "/api/v1/occurrences",
        json={
            "trip_id": trip["id"],
            "type": "UNSUPPORTED",
            "description": "Tipo inválido.",
        },
        headers=scenario.manager_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
