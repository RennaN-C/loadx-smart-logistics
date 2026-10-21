"""Audited, atomic cancellation of trips that have not started loading.

The distribution part remains physically traceable and can be reprocessed.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, Uuid, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.exceptions import ApiError
from app.database.base import Base
from app.modules.deliveries.cancellation_preflight import assess_cancellation
from app.modules.deliveries.models import Delivery
from app.modules.deliveries.service import (
    TripAccessForbiddenError,
    TripNotFoundError,
    TripService,
)
from app.modules.load_planning.distribution_repository import LoadDistributionRepository
from app.modules.load_planning.repository import LoadPlanRepository
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.status_history.schemas import StatusHistoryCreate
from app.modules.status_history.service import StatusHistoryService
from app.modules.trucks.service import TruckService
from app.modules.users.models import User


class TripCancellation(Base):
    __tablename__ = "trip_cancellations"
    __table_args__ = (
        UniqueConstraint("trip_id", name="uq_trip_cancellations__trip"),
        UniqueConstraint("idempotency_key", name="uq_trip_cancellations__request"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TripCancellationRequest(BaseModel):
    reason: str = Field(min_length=8, max_length=500)
    idempotency_key: uuid.UUID

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if len(value.strip()) < 8:
            raise ValueError("reason must explain the cancellation")
        return value.strip()


class TripCancellationRead(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    actor_id: uuid.UUID
    idempotency_key: uuid.UUID
    reason: str
    created_at: datetime
    status: str

    model_config = ConfigDict(extra="forbid")


class TripCancellationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripService(db)
        self.history = StatusHistoryService(db)

    def cancel(
        self,
        trip_id: uuid.UUID,
        payload: TripCancellationRequest,
        *,
        current_user: User,
    ) -> TripCancellationRead:
        try:
            result = self._stage(trip_id, payload, current_user=current_user)
            self.db.commit()
            return result
        except IntegrityError as exc:
            self.db.rollback()
            raise ApiError(
                409,
                "TRIP_CANCELLATION_CONFLICT",
                "Conflito entre operacoes de cancelamento.",
            ) from exc
        except Exception:
            self.db.rollback()
            raise

    def _stage(
        self,
        trip_id: uuid.UUID,
        payload: TripCancellationRequest,
        *,
        current_user: User,
    ) -> TripCancellationRead:
        # Same lock order as OC90: trip, deliveries, then plan/truck/orders.
        try:
            trip = self.trips.get_trip(
                trip_id, current_user=current_user, for_update=True
            )
        except TripNotFoundError:
            raise ApiError(404, "TRIP_NOT_FOUND", "Viagem nao encontrada.") from None
        except TripAccessForbiddenError:
            raise ApiError(
                403, "AUTH_FORBIDDEN", "Acesso nao autorizado a viagem."
            ) from None

        deliveries = tuple(self.trips.repository.list_deliveries_for_update(trip.id))
        existing = self.db.scalar(
            select(TripCancellation).where(TripCancellation.trip_id == trip.id)
        )
        if existing is not None:
            if (
                existing.idempotency_key != payload.idempotency_key
                or existing.reason != payload.reason
                or existing.actor_id != current_user.id
            ):
                raise ApiError(
                    409,
                    "TRIP_CANCELLATION_ALREADY_EXISTS",
                    "Viagem ja cancelada com outra solicitacao.",
                )
            return self._result(existing, status=trip.status)

        plan = LoadPlanRepository(self.db).get_for_update(trip.load_plan_id)
        if plan is None or plan.status != "APPROVED":
            raise ApiError(
                409,
                "TRIP_CANCELLATION_PLAN_INVALID",
                "Plano original nao esta aprovado.",
            )
        # A loading session is a physical claim, even in status PENDING.
        loading = LoadingReferenceService(self.db).get_by_load_plan_id(plan.id)
        part_ids = {row.distribution_part_id for row in deliveries}
        if len(part_ids) > 1:
            raise ApiError(
                409,
                "TRIP_CANCELLATION_INVALID_PARTS",
                "Viagem tem partes de distribuicao inconsistentes.",
            )
        is_multi = bool(part_ids and None not in part_ids)
        blockers = assess_cancellation(
            status=trip.status,
            delivery_statuses=tuple(row.status for row in deliveries),
            has_distribution_part=False,  # handled transactionally below
            loading_status=loading.status if loading else None,
        )
        if blockers:
            raise ApiError(
                409,
                "TRIP_CANCELLATION_BLOCKED",
                "Operacao nao elegivel: " + ", ".join(blockers),
            )
        if len({row.order_id for row in deliveries}) != len(deliveries):
            raise ApiError(
                409,
                "TRIP_CANCELLATION_DUPLICATE_ORDER",
                "Entregas duplicadas na viagem.",
            )
        TruckService(self.db).get_truck_for_update(plan.truck_id)
        distribution = None
        part = None
        if is_multi:
            part_id = next(iter(part_ids))
            part = LoadDistributionRepository(self.db).plan_part(plan.id)
            if part is None or part.id != part_id or part.load_plan_id != plan.id:
                raise ApiError(
                    409,
                    "TRIP_CANCELLATION_PART_CHANGED",
                    "Parte de distribuicao foi substituida.",
                )
            distribution = LoadDistributionRepository(self.db).get(
                part.distribution_id, for_update=True
            )
            if (
                distribution is None
                or distribution.status not in {"APPROVED", "INCOMPLETE"}
                or part.status != "APPROVED"
            ):
                raise ApiError(
                    409,
                    "TRIP_CANCELLATION_DISTRIBUTION_INVALID",
                    "Distribuicao nao esta no estado esperado.",
                )
            # Check that canceled part is current, without changing its volumes.
            part = next((p for p in distribution.parts if p.id == part_id), None)
            if part is None or part.status != "APPROVED":
                raise ApiError(
                    409,
                    "TRIP_CANCELLATION_PART_CHANGED",
                    "Parte de distribuicao foi alterada.",
                )

        ids = sorted({row.order_id for row in deliveries}, key=lambda x: x.int)
        orders = self.trips.order_service.get_orders(ids, for_update=True)
        eligible = {"PLANNED", "IN_TRANSIT"} if is_multi else {"PLANNED"}
        if {o.id for o in orders} != set(ids) or any(
            o.status not in eligible for o in orders
        ):
            raise ApiError(
                409,
                "TRIP_CANCELLATION_ORDER_CHANGED",
                "Pedido ja possui movimentacao operacional.",
            )

        # No historical receipt, delivery or physical volume is deleted.
        for delivery in deliveries:
            delivery.status = "CANCELED"
            self._history(
                "DELIVERY", delivery.id, "PENDING", "CANCELED", current_user.id
            )

        trip.status = "CANCELED"
        self._history("TRIP", trip.id, "SCHEDULED", "CANCELED", current_user.id)
        plan.status = "CANCELED"  # preserve approved_at as historical fact
        self._history("LOAD_PLAN", plan.id, "APPROVED", "CANCELED", current_user.id)

        if is_multi and distribution is not None and part is not None:
            part.status = "CANCELED"
            self._history(
                "LOAD_DISTRIBUTION_PART",
                part.id,
                "APPROVED",
                "CANCELED",
                current_user.id,
            )
            previous = distribution.status
            distribution.status = "INCOMPLETE"
            if previous != "INCOMPLETE":
                self._history(
                    "LOAD_DISTRIBUTION",
                    distribution.id,
                    previous,
                    "INCOMPLETE",
                    current_user.id,
                )
            # Preserve active volume identity and order claim for reprocessing.
        else:
            for order in orders:
                other = self.db.scalar(
                    select(Delivery.id)
                    .where(
                        Delivery.order_id == order.id,
                        Delivery.trip_id != trip.id,
                        Delivery.status != "CANCELED",
                    )
                    .limit(1)
                )
                if other is not None:
                    raise ApiError(
                        409,
                        "TRIP_CANCELLATION_ORDER_CLAIMED",
                        "Pedido possui entrega em outra viagem.",
                    )
                order.status = "READY"
                self._history("ORDER", order.id, "PLANNED", "READY", current_user.id)

        row = TripCancellation(
            trip_id=trip.id,
            actor_id=current_user.id,
            idempotency_key=payload.idempotency_key,
            reason=payload.reason,
        )
        self.db.add(row)
        self.db.flush()
        self.db.refresh(row)
        return self._result(row, status=trip.status)

    def _history(
        self,
        kind: str,
        identifier: uuid.UUID,
        before: str,
        after: str,
        actor: uuid.UUID,
    ) -> None:
        self.history.stage_status_change(
            StatusHistoryCreate(
                entity_type=kind,
                entity_id=identifier,
                old_status=before,
                new_status=after,
                changed_by=actor,
            )
        )

    @staticmethod
    def _result(row: TripCancellation, *, status: str) -> TripCancellationRead:
        return TripCancellationRead(
            id=row.id,
            trip_id=row.trip_id,
            actor_id=row.actor_id,
            idempotency_key=row.idempotency_key,
            reason=row.reason,
            created_at=row.created_at,
            status=status,
        )
