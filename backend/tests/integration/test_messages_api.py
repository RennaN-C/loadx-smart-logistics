def test_interpret_message_returns_documented_arrived_intent(client) -> None:
    response = client.post(
        "/api/v1/messages/interpret",
        json={
            "driver_phone": "+5500000000000",
            "message": "Ja cheguei no cliente",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "intent": "ARRIVED",
        "confidence": 0.91,
        "allowed": True,
        "action": "UPDATE_DELIVERY_STATUS",
    }


def test_interpret_unknown_message_does_not_allow_an_action(client) -> None:
    response = client.post(
        "/api/v1/messages/interpret",
        json={
            "driver_phone": "+5500000000000",
            "message": "Preciso de ajuda",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "intent": None,
        "confidence": 0,
        "allowed": False,
        "action": None,
    }
