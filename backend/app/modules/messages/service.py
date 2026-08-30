import unicodedata
from typing import ClassVar

from sqlalchemy.orm import Session

from app.integrations.whatsapp.provider import (
    IncomingWhatsAppMessage,
    OutgoingWhatsAppMessage,
    WhatsAppProvider,
)
from app.modules.deliveries.models import Trip
from app.modules.deliveries.reference_service import DeliveryReferenceService
from app.modules.deliveries.service import (
    DeliveryStatusTransitionNotAllowedError,
    DeliveryTripNotInRouteError,
    TripAccessForbiddenError,
    TripLoadingNotFinishedError,
    TripService,
    TripStatusTransitionNotAllowedError,
)
from app.modules.drivers.repository import DriverRepository
from app.modules.messages.schemas import MessageInterpretResponse
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


class MessageInterpreterService:
    """Interpreta somente frases e intenções aprovadas para o MVP."""

    _commands: ClassVar[dict[str, tuple[str, str, float]]] = {
        "iniciar viagem": ("START_TRIP", "UPDATE_TRIP_STATUS", 1.0),
        "ja cheguei no cliente": ("ARRIVED", "UPDATE_DELIVERY_STATUS", 0.91),
        "cheguei": ("ARRIVED", "UPDATE_DELIVERY_STATUS", 1.0),
        "iniciar entrega": ("START_DELIVERY", "UPDATE_DELIVERY_STATUS", 1.0),
        "finalizar entrega": ("FINISH_DELIVERY", "UPDATE_DELIVERY_STATUS", 1.0),
        "status": ("STATUS", "READ_TRIP_STATUS", 1.0),
        "proxima entrega": ("NEXT_DELIVERY", "READ_DELIVERY_STATUS", 1.0),
    }

    def interpret_message(self, message: str) -> MessageInterpretResponse:
        command = self._commands.get(self._normalize(message))
        if command is None:
            return MessageInterpretResponse(
                intent=None,
                confidence=0,
                allowed=False,
                action=None,
            )
        intent, action, confidence = command
        return MessageInterpretResponse(
            intent=intent,
            confidence=confidence,
            allowed=True,
            action=action,
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


class ControlledMessageService:
    """Executa comandos controlados usando apenas fronteiras públicas do domínio."""

    _domain_errors = (
        DeliveryStatusTransitionNotAllowedError,
        DeliveryTripNotInRouteError,
        TripAccessForbiddenError,
        TripLoadingNotFinishedError,
        TripStatusTransitionNotAllowedError,
    )

    def __init__(self, db: Session, provider: WhatsAppProvider) -> None:
        self.provider = provider
        self.interpreter = MessageInterpreterService()
        self.driver_repository = DriverRepository(db)
        self.user_repository = UserRepository(db)
        self.delivery_reference_service = DeliveryReferenceService(db)
        self.trip_service = TripService(db)

    def process(self, driver_phone: str, message: str) -> MessageInterpretResponse:
        incoming = self.provider.receive_message(
            IncomingWhatsAppMessage(sender_phone=driver_phone, content=message)
        )
        interpreted = self.interpreter.interpret_message(incoming.content)
        if not interpreted.allowed:
            return self._respond(
                driver_phone,
                interpreted,
                "Comando não reconhecido.",
            )

        driver = self.driver_repository.get_by_phone(driver_phone)
        if driver is None or not driver.active:
            return self._respond(
                driver_phone,
                interpreted,
                "Motorista não identificado ou inativo.",
            )
        user = self.user_repository.get_by_driver_id(driver.id)
        if user is None or not user.active or user.role != "DRIVER":
            return self._respond(
                driver_phone,
                interpreted,
                "Motorista sem usuário ativo vinculado.",
            )
        trip = self.delivery_reference_service.get_active_trip_for_driver(driver.id)
        if trip is None:
            return self._respond(
                driver_phone,
                interpreted,
                "Nenhuma viagem ativa e inequívoca foi encontrada.",
            )

        try:
            return self._execute_command(driver_phone, interpreted, trip, user)
        except self._domain_errors:
            return self._respond(
                driver_phone,
                interpreted,
                "Comando não permitido para o estado atual.",
                trip_id=trip.id,
            )

    def _execute_command(
        self,
        driver_phone: str,
        interpreted: MessageInterpretResponse,
        trip: Trip,
        user: User,
    ) -> MessageInterpretResponse:
        if interpreted.intent == "START_TRIP":
            changed = self.trip_service.change_trip_status(
                trip.id, "IN_ROUTE", current_user=user
            )
            return self._respond(
                driver_phone,
                interpreted,
                "Viagem iniciada com sucesso.",
                executed=True,
                trip_id=changed.id,
            )

        delivery = self.delivery_reference_service.get_current_delivery(trip.id)
        if interpreted.intent in {"ARRIVED", "START_DELIVERY"}:
            if delivery is None:
                return self._respond(
                    driver_phone,
                    interpreted,
                    "Nenhuma entrega pendente encontrada.",
                )
            changed_delivery = self.trip_service.change_delivery_status(
                delivery.id, "IN_DELIVERY", current_user=user
            )
            return self._respond(
                driver_phone,
                interpreted,
                "Entrega iniciada com sucesso.",
                executed=True,
                trip_id=trip.id,
                delivery_id=changed_delivery.id,
            )
        if interpreted.intent == "FINISH_DELIVERY":
            if delivery is None:
                return self._respond(
                    driver_phone,
                    interpreted,
                    "Nenhuma entrega em andamento encontrada.",
                )
            changed_delivery = self.trip_service.change_delivery_status(
                delivery.id, "DELIVERED", current_user=user
            )
            return self._respond(
                driver_phone,
                interpreted,
                "Entrega finalizada com sucesso.",
                executed=True,
                trip_id=trip.id,
                delivery_id=changed_delivery.id,
            )
        if interpreted.intent == "STATUS":
            return self._respond(
                driver_phone,
                interpreted,
                f"Status da viagem: {trip.status}.",
                executed=True,
                trip_id=trip.id,
            )
        if interpreted.intent == "NEXT_DELIVERY" and delivery is not None:
            return self._respond(
                driver_phone,
                interpreted,
                f"Próxima entrega: sequência {delivery.sequence}, status {delivery.status}.",
                executed=True,
                trip_id=trip.id,
                delivery_id=delivery.id,
            )
        return self._respond(
            driver_phone,
            interpreted,
            "Comando reconhecido, mas indisponível no estado atual.",
            trip_id=trip.id,
        )

    def _respond(
        self,
        phone: str,
        interpreted: MessageInterpretResponse,
        confirmation: str,
        *,
        executed: bool = False,
        trip_id=None,
        delivery_id=None,
    ) -> MessageInterpretResponse:
        self.provider.send_response(
            OutgoingWhatsAppMessage(recipient_phone=phone, content=confirmation)
        )
        return interpreted.model_copy(
            update={
                "executed": executed,
                "confirmation": confirmation,
                "trip_id": trip_id,
                "delivery_id": delivery_id,
            }
        )
