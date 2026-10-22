"""Bounded activity agenda aggregated by PostgreSQL, with effective RBAC."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, literal, select, union_all
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.access_profiles.catalog import Permission, has_permission
from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.exception_models import DeliveryException
from app.modules.deliveries.cancellation_service import TripCancellation
from app.modules.deliveries.interruption_service import TripInterruptionEvent
from app.modules.drivers.service import DriverNotFoundError, DriverService
from app.modules.load_planning.models import LoadPlan
from app.modules.loading.models import LoadingSession
from app.modules.operational_agenda.schemas import (
    AgendaEvent,
    AgendaKind,
    OperationalAgendaRead,
)
from app.modules.users.models import User

MAX_DAYS = 7
MAX_EVENTS = 1000


@dataclass(frozen=True, slots=True)
class AgendaFilters:
    start: datetime
    end: datetime
    kind: AgendaKind | None = None
    truck_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None


def validate_window(filters: AgendaFilters) -> AgendaFilters:
    if (
        filters.start.tzinfo is None
        or filters.start.tzinfo.utcoffset(filters.start) is None
        or filters.end.tzinfo is None
        or filters.end.tzinfo.utcoffset(filters.end) is None
    ):
        raise ApiError(
            422, "AGENDA_TIMEZONE_REQUIRED", "Informe datas com fuso horario."
        )
    start = filters.start.astimezone(UTC)
    end = filters.end.astimezone(UTC)
    if end <= start or end - start > timedelta(days=MAX_DAYS):
        raise ApiError(
            422, "AGENDA_PERIOD_INVALID", "O periodo deve ter ate sete dias."
        )
    return AgendaFilters(start, end, filters.kind, filters.truck_id, filters.driver_id)


class OperationalAgendaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.drivers = DriverService(db)

    def _permitted_driver(
        self, requested: uuid.UUID | None, current_user: User
    ) -> uuid.UUID | None:
        if has_permission(current_user, Permission.TRIPS_READ):
            return requested
        if current_user.role != "DRIVER" or current_user.driver_id is None:
            raise ApiError(403, "AUTH_FORBIDDEN", "Acesso a agenda nao autorizado.")
        try:
            driver = self.drivers.get_driver(current_user.driver_id)
        except DriverNotFoundError:
            raise ApiError(403, "AUTH_FORBIDDEN", "Motorista indisponivel.") from None
        if not driver.active or (
            requested is not None and requested != current_user.driver_id
        ):
            raise ApiError(403, "AUTH_FORBIDDEN", "Motorista nao autorizado.")
        return current_user.driver_id

    def get(
        self, requested: AgendaFilters, *, current_user: User
    ) -> OperationalAgendaRead:
        filters = validate_window(requested)
        driver_id = self._permitted_driver(filters.driver_id, current_user)

        def trip_event(kind, timestamp):
            return (
                select(
                    literal(kind).label("kind"),
                    Trip.id.label("resource_id"),
                    Trip.id.label("trip_id"),
                    timestamp.label("occurred_at"),
                    LoadPlan.truck_id.label("truck_id"),
                    Trip.driver_id.label("driver_id"),
                )
                .select_from(Trip)
                .join(LoadPlan, LoadPlan.id == Trip.load_plan_id)
            )

        def delivery_event():
            return (
                select(
                    literal("DELIVERY_COMPLETED").label("kind"),
                    Delivery.id.label("resource_id"),
                    Trip.id.label("trip_id"),
                    Delivery.delivered_at.label("occurred_at"),
                    LoadPlan.truck_id.label("truck_id"),
                    Trip.driver_id.label("driver_id"),
                )
                .select_from(Delivery)
                .join(Trip, Trip.id == Delivery.trip_id)
                .join(LoadPlan, LoadPlan.id == Trip.load_plan_id)
            )

        def loading_event(kind, timestamp):
            return (
                select(
                    literal(kind).label("kind"),
                    LoadingSession.id.label("resource_id"),
                    Trip.id.label("trip_id"),
                    timestamp.label("occurred_at"),
                    LoadPlan.truck_id.label("truck_id"),
                    Trip.driver_id.label("driver_id"),
                )
                .select_from(LoadingSession)
                .join(Trip, Trip.load_plan_id == LoadingSession.load_plan_id)
                .join(LoadPlan, LoadPlan.id == Trip.load_plan_id)
            )

        def audited_trip_event(model, kind, timestamp):
            return (
                select(
                    literal(kind).label("kind") if isinstance(kind, str) else kind.label("kind"),
                    model.id.label("resource_id"),
                    Trip.id.label("trip_id"),
                    timestamp.label("occurred_at"),
                    LoadPlan.truck_id.label("truck_id"),
                    Trip.driver_id.label("driver_id"),
                )
                .select_from(model)
                .join(Trip, model.trip_id == Trip.id)
                .join(LoadPlan, LoadPlan.id == Trip.load_plan_id)
            )

        activity = union_all(
            trip_event("TRIP_CREATED", Trip.created_at),
            trip_event("TRIP_STARTED", Trip.started_at),
            trip_event("TRIP_FINISHED", Trip.finished_at),
            loading_event("LOADING_STARTED", LoadingSession.started_at),
            loading_event("LOADING_FINISHED", LoadingSession.finished_at),
            delivery_event(),
            audited_trip_event(
                DeliveryException, "DELIVERY_EXCEPTION", DeliveryException.created_at
            ),
            audited_trip_event(
                TripCancellation, "TRIP_CANCELED", TripCancellation.created_at
            ),
            audited_trip_event(
                TripInterruptionEvent,
                case(
                    (TripInterruptionEvent.action == "INTERRUPTED", "TRIP_INTERRUPTED"),
                    else_="TRIP_RESUMED",
                ),
                TripInterruptionEvent.created_at,
            ),
        ).subquery()
        query = select(activity).where(
            activity.c.occurred_at >= filters.start,
            activity.c.occurred_at < filters.end,
        )
        if driver_id is not None:
            query = query.where(activity.c.driver_id == driver_id)
        if filters.truck_id is not None:
            query = query.where(activity.c.truck_id == filters.truck_id)
        if filters.kind is not None:
            query = query.where(activity.c.kind == filters.kind)
        query = query.order_by(
            activity.c.occurred_at, activity.c.kind, activity.c.resource_id
        ).limit(MAX_EVENTS + 1)
        rows = self.db.execute(query).mappings().all()
        if len(rows) > MAX_EVENTS:
            raise ApiError(
                409,
                "AGENDA_TOO_LARGE",
                "Muitos eventos no periodo; refine os filtros.",
            )
        items = [AgendaEvent.model_validate(dict(row)) for row in rows]
        return OperationalAgendaRead(
            start=filters.start, end=filters.end, total=len(items), items=items
        )
