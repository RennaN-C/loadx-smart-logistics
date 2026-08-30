from fastapi.testclient import TestClient

from tests.integration.test_deliveries_api import create_trip, seed_operational_scenario


def finish_loading(client: TestClient, scenario) -> None:
    created = client.post(
        "/api/v1/loading-sessions",
        json={"load_plan_id": str(scenario.load_plan_id)},
        headers=scenario.checker_headers,
    )
    loading = created.json()
    client.patch(
        f"/api/v1/loading-sessions/{loading['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=scenario.checker_headers,
    )
    for item in loading["items"]:
        client.patch(
            f"/api/v1/loading-sessions/{loading['id']}/items/{item['id']}",
            json={"status": "CHECKED"},
            headers=scenario.checker_headers,
        )
    finished = client.patch(
        f"/api/v1/loading-sessions/{loading['id']}/status",
        json={"status": "FINISHED"},
        headers=scenario.checker_headers,
    )
    assert finished.status_code == 200


def send_command(client: TestClient, message: str):
    return client.post(
        "/api/v1/messages/interpret",
        json={"driver_phone": "5500000000000", "message": message},
    )


def test_controlled_message_executes_trip_and_delivery_public_services(
    client: TestClient,
    session_factory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    trip = create_trip(client, scenario)
    finish_loading(client, scenario)

    started_trip = send_command(client, "INICIAR VIAGEM")
    assert started_trip.status_code == 200
    assert started_trip.json() == {
        "intent": "START_TRIP",
        "confidence": 1.0,
        "allowed": True,
        "action": "UPDATE_TRIP_STATUS",
        "executed": True,
        "confirmation": "Viagem iniciada com sucesso.",
        "trip_id": trip["id"],
        "delivery_id": None,
    }

    started_delivery = send_command(client, "Já cheguei no cliente")
    assert started_delivery.status_code == 200
    assert started_delivery.json()["executed"] is True
    assert started_delivery.json()["confirmation"] == "Entrega iniciada com sucesso."
    assert started_delivery.json()["delivery_id"] == trip["deliveries"][0]["id"]

    finished_delivery = send_command(client, "FINALIZAR ENTREGA")
    assert finished_delivery.status_code == 200
    assert finished_delivery.json()["executed"] is True
    assert finished_delivery.json()["confirmation"] == (
        "Entrega finalizada com sucesso."
    )


def test_controlled_message_rejects_unknown_driver_and_state(
    client: TestClient,
    session_factory,
) -> None:
    scenario = seed_operational_scenario(session_factory)
    create_trip(client, scenario)

    unknown_driver = client.post(
        "/api/v1/messages/interpret",
        json={"driver_phone": "5599999999999", "message": "INICIAR VIAGEM"},
    )
    assert unknown_driver.status_code == 200
    assert unknown_driver.json()["executed"] is False
    assert unknown_driver.json()["confirmation"] == (
        "Motorista não identificado ou inativo."
    )

    loading_not_finished = send_command(client, "INICIAR VIAGEM")
    assert loading_not_finished.status_code == 200
    assert loading_not_finished.json()["executed"] is False
    assert loading_not_finished.json()["confirmation"] == (
        "Comando não permitido para o estado atual."
    )


def test_unknown_message_does_not_execute_an_action(client: TestClient) -> None:
    response = client.post(
        "/api/v1/messages/interpret",
        json={
            "driver_phone": "5500000000000",
            "message": "Preciso de ajuda",
        },
    )

    assert response.status_code == 200
    assert response.json()["allowed"] is False
    assert response.json()["executed"] is False
    assert response.json()["confirmation"] == "Comando não reconhecido."
