"""First safe, append-only slice of OC94 exception handling."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.deliveries.exception_models import DeliveryException
from app.modules.deliveries.exception_schemas import (
    DeliveryExceptionCreate,
    DeliveryExceptionRead,
)
from app.modules.deliveries.models import Trip

_FAILURE_CODES = frozenset(
    {"CUSTOMER_ABSENT", "REFUSED", "DAMAGED", "OPERATIONAL_FAILURE"}
)

from app.modules.deliveries.service import (
    DeliveryNotFoundError,
    TripAccessForbiddenError,
    TripNotFoundError,
    TripService,
)
from app.modules.users.models import User


class DeliveryExceptionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripService(db)

    def _authorized_delivery(
        self, delivery_id: uuid.UUID, *, current_user: User, operate: bool
    ):
        try:
            return self.trips.get_delivery_for_access(
                delivery_id, current_user=current_user, operate=operate
            )
        except TripAccessForbiddenError:
            raise ApiError(
                403, "AUTH_FORBIDDEN", "Usuario sem permissao para esta acao."
            ) from None
        except (TripNotFoundError, DeliveryNotFoundError):
            raise ApiError(
                404, "DELIVERY_NOT_FOUND", "Entrega nao encontrada."
            ) from None

    def list_for_delivery(
        self, delivery_id: uuid.UUID, *, current_user: User
    ) -> list[DeliveryExceptionRead]:
        self._authorized_delivery(delivery_id, current_user=current_user, operate=False)
        rows = self.db.scalars(
            select(DeliveryException)
            .where(DeliveryException.delivery_id == delivery_id)
            .order_by(DeliveryException.created_at, DeliveryException.id)
        ).all()
        return [DeliveryExceptionRead.model_validate(row) for row in rows]

    def register(
        self,
        delivery_id: uuid.UUID,
        data: DeliveryExceptionCreate,
        *,
        current_user: User,
    ) -> tuple[DeliveryExceptionRead, bool]:
        try:
            # OC90 serializes operations with trip -> deliveries locks.
            delivery = self._authorized_delivery(
                delivery_id, current_user=current_user, operate=True
            )
            previous = self.db.scalar(
                select(DeliveryException).where(
                    DeliveryException.delivery_id == delivery_id,
                    DeliveryException.idempotency_key == data.idempotency_key,
                )
            )
            if previous is not None:
                if (
                    previous.code != data.code
                    or previous.reason != data.reason
                    or previous.scheduled_for != data.scheduled_for
                ):
                    raise ApiError(
                        409,
                        "DELIVERY_EXCEPTION_IDEMPOTENCY_CONFLICT",
                        "A chave ja foi utilizada com outros dados.",
                    )
                result = DeliveryExceptionRead.model_validate(previous)
                self.db.commit()
                return result, False

            trip = self.db.get(Trip, delivery.trip_id)
            if (
                trip is None
                or trip.status != "IN_ROUTE"
                or delivery.status == "DELIVERED"
            ):
                raise ApiError(
                    409,
                    "DELIVERY_EXCEPTION_NOT_ELIGIBLE",
                    "A entrega nao admite ocorrencias neste estado.",
                )
            if data.scheduled_for is not None and data.scheduled_for <= datetime.now(
                UTC
            ):
                raise ApiError(
                    422,
                    "DELIVERY_EXCEPTION_INVALID_SCHEDULE",
                    "O reagendamento deve estar no futuro.",
                )

            last = self.db.scalar(
                select(DeliveryException)
                .where(DeliveryException.delivery_id == delivery_id)
                .order_by(
                    DeliveryException.created_at.desc(),
                    DeliveryException.id.desc(),
                )
                .limit(1)
            )
            if data.code in _FAILURE_CODES:
                if last is not None and last.code != "RESUMED":
                    raise ApiError(
                        409,
                        "DELIVERY_EXCEPTION_PENDING",
                        "Resolva a ocorrencia anterior antes de abrir outra.",
                    )
            elif data.code == "RESCHEDULED":
                if last is None or last.code not in _FAILURE_CODES:
                    raise ApiError(
                        409,
                        "DELIVERY_EXCEPTION_TRANSITION_INVALID",
                        "Reagendamento exige uma falha anterior em aberto.",
                    )
            elif data.code == "RESUMED":
                if last is None or (
                    last.code not in _FAILURE_CODES and last.code != "RESCHEDULED"
                ):
                    raise ApiError(
                        409,
                        "DELIVERY_EXCEPTION_TRANSITION_INVALID",
                        "Retomada exige uma falha ou reagendamento pendente.",
                    )
                if last.scheduled_for is not None and last.scheduled_for > datetime.now(
                    UTC
                ):
                    raise ApiError(
                        409,
                        "DELIVERY_EXCEPTION_SCHEDULE_PENDING",
                        "A nova tentativa ainda nao atingiu o horario combinado.",
                    )

            event = DeliveryException(
                delivery_id=delivery.id,
                trip_id=delivery.trip_id,
                code=data.code,
                reason=data.reason,
                actor_id=current_user.id,
                idempotency_key=data.idempotency_key,
                scheduled_for=data.scheduled_for,
            )
            self.db.add(event)
            self.db.flush()
            result = DeliveryExceptionRead.model_validate(event)
            self.db.commit()
            return result, True
        except Exception:
            self.db.rollback()
            raise
