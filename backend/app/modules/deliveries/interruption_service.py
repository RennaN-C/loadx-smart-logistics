"""OC94: audited pause/resume of an in-route trip, without releasing cargo."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.exceptions import ApiError
from app.database.base import Base
from app.modules.deliveries.service import (
    TripAccessForbiddenError,
    TripNotFoundError,
    TripService,
)
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import StatusHistoryService
from app.modules.users.models import User


class TripInterruptionEvent(Base):
    __tablename__ = "trip_interruption_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_trip_interruption_events__request"),
        Index("ix_trip_interruption_events__trip_id_created_at", "trip_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TripInterruptionRequest(BaseModel):
    reason: str = Field(min_length=8, max_length=500)
    idempotency_key: uuid.UUID

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("reason")
    @classmethod
    def check_reason(cls, reason: str) -> str:
        if len(reason.strip()) < 8:
            raise ValueError("Informe o motivo operacional detalhado.")
        return reason.strip()


class TripInterruptionRead(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    actor_id: uuid.UUID
    idempotency_key: uuid.UUID
    action: str
    reason: str
    created_at: datetime
    trip_status: str

    model_config = ConfigDict(extra="forbid")


class TripInterruptionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripService(db)
        self.history = StatusHistoryService(db)

    @staticmethod
    def as_read(event: TripInterruptionEvent, status: str) -> TripInterruptionRead:
        return TripInterruptionRead(
            id=event.id,
            trip_id=event.trip_id,
            actor_id=event.actor_id,
            idempotency_key=event.idempotency_key,
            action=event.action,
            reason=event.reason,
            created_at=event.created_at,
            trip_status=status,
        )

    def _trip(self, identifier: uuid.UUID, *, user: User, lock: bool):
        try:
            return self.trips.get_trip(identifier, current_user=user, for_update=lock)
        except TripNotFoundError:
            raise ApiError(404, "TRIP_NOT_FOUND", "Viagem nao encontrada.") from None
        except TripAccessForbiddenError:
            raise ApiError(403, "AUTH_FORBIDDEN", "Acesso negado a viagem.") from None

    def history_for(self, trip_id: uuid.UUID, *, user: User) -> list[TripInterruptionRead]:
        trip = self._trip(trip_id, user=user, lock=False)
        records = self.db.scalars(
            select(TripInterruptionEvent)
            .where(TripInterruptionEvent.trip_id == trip.id)
            .order_by(TripInterruptionEvent.created_at, TripInterruptionEvent.id)
        ).all()
        return [self.as_read(record, trip.status) for record in records]

    def transition(
        self,
        trip_id: uuid.UUID,
        data: TripInterruptionRequest,
        *,
        user: User,
        action: str,
    ) -> TripInterruptionRead:
        try:
            trip = self._trip(trip_id, user=user, lock=True)
            prior = self.db.scalar(
                select(TripInterruptionEvent).where(
                    TripInterruptionEvent.idempotency_key == data.idempotency_key
                )
            )
            if prior is not None:
                if (
                    prior.trip_id != trip_id
                    or prior.actor_id != user.id
                    or prior.action != action
                    or prior.reason != data.reason
                ):
                    raise ApiError(
                        409, "TRIP_INTERRUPTION_IDEMPOTENCY_CONFLICT",
                        "Chave de idempotencia ja utilizada com outros dados.",
                    )
                return self.as_read(prior, trip.status)

            before = "IN_ROUTE" if action == "INTERRUPTED" else "INTERRUPTED"
            after = "INTERRUPTED" if action == "INTERRUPTED" else "IN_ROUTE"
            if trip.status != before:
                raise ApiError(
                    409, "TRIP_INTERRUPTION_INVALID_TRANSITION",
                    "Viagem nao esta no estado exigido para esta operacao.",
                )

            # No delivery, order, load plan, vehicle, driver, timestamps, or
            # physical allocation are mutated. The trip remains reserved.
            trip.status = after
            event = TripInterruptionEvent(
                trip_id=trip.id,
                actor_id=user.id,
                idempotency_key=data.idempotency_key,
                action=action,
                reason=data.reason,
                created_at=datetime.now(UTC),
            )
            self.db.add(event)
            self.history.stage_status_change(
                StatusHistoryCreate(
                    entity_type="TRIP",
                    entity_id=trip.id,
                    old_status=before,
                    new_status=after,
                    changed_by=user.id,
                )
            )
            self.db.flush()
            self.db.refresh(event)
            result = self.as_read(event, trip.status)
            self.db.commit()
            return result
        except IntegrityError as exc:
            self.db.rollback()
            raise ApiError(
                409, "TRIP_INTERRUPTION_CONFLICT", "Conflito de operacao concorrente."
            ) from exc
        except Exception:
            self.db.rollback()
            raise
