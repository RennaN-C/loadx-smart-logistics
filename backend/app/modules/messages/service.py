import unicodedata

from app.modules.messages.schemas import MessageInterpretResponse


class MessageInterpreterService:
    """Interpreta somente frases e intenções aprovadas para o MVP."""

    _arrived_messages = {"ja cheguei no cliente"}

    def interpret_message(self, message: str) -> MessageInterpretResponse:
        if self._normalize(message) in self._arrived_messages:
            return MessageInterpretResponse(
                intent="ARRIVED",
                confidence=0.91,
                allowed=True,
                action="UPDATE_DELIVERY_STATUS",
            )

        return MessageInterpretResponse(
            intent=None,
            confidence=0,
            allowed=False,
            action=None,
        )

    @staticmethod
    def _normalize(message: str) -> str:
        normalized = unicodedata.normalize("NFD", message)
        without_accents = "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Mn"
        )
        return " ".join(without_accents.casefold().split())
