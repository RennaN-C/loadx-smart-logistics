import pytest

from app.modules.messages.service import MessageInterpreterService


@pytest.mark.parametrize(
    "message",
    [
        "Já cheguei no cliente",
        "JA CHEGUEI NO CLIENTE",
        "  ja   cheguei no cliente  ",
    ],
)
def test_interprets_documented_arrived_message(message: str) -> None:
    response = MessageInterpreterService().interpret_message(message)

    assert response.intent == "ARRIVED"
    assert response.confidence == 0.91
    assert response.allowed is True
    assert response.action == "UPDATE_DELIVERY_STATUS"


def test_unknown_message_does_not_allow_an_action() -> None:
    response = MessageInterpreterService().interpret_message("Preciso de ajuda")

    assert response.intent is None
    assert response.confidence == 0
    assert response.allowed is False
    assert response.action is None
