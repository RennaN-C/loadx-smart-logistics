"""Server-side management summary. Counts are operational facts, not estimates."""

import csv
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import StringIO

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.deliveries.models import Delivery, Trip
from app.modules.load_planning.models import LoadPlan
from app.modules.occurrences.models import Occurrence
from app.modules.reports.service import ReportService


@dataclass(frozen=True, slots=True)
class ManagementFilters:
    start: datetime
    end: datetime
    truck_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None


def validate_window(filters: ManagementFilters) -> ManagementFilters:
    if (
        filters.start.tzinfo is None
        or filters.start.tzinfo.utcoffset(filters.start) is None
        or filters.end.tzinfo is None
        or filters.end.tzinfo.utcoffset(filters.end) is None
    ):
        raise ApiError(
            422, "REPORT_PERIOD_TIMEZONE_REQUIRED", "Informe datas com fuso horario."
        )
    start = filters.start.astimezone(UTC)
    end = filters.end.astimezone(UTC)
    if end <= start or end - start > timedelta(days=93):
        raise ApiError(
            422,
            "REPORT_PERIOD_INVALID",
            "O periodo deve ter ate 93 dias e fim posterior ao inicio.",
        )
    return ManagementFilters(
        start=start, end=end, truck_id=filters.truck_id, driver_id=filters.driver_id
    )


@dataclass(frozen=True, slots=True)
class ManagementSummary:
    start: datetime
    end: datetime
    trips_created: int
    trips_started: int
    trips_finished: int
    deliveries_completed: int
    orders_with_completed_leg: int
    occurrences_registered: int

    def metrics(self) -> tuple[tuple[str, int], ...]:
        return (
            ("Viagens criadas", self.trips_created),
            ("Viagens iniciadas", self.trips_started),
            ("Viagens finalizadas", self.trips_finished),
            ("Pernas de entrega concluidas", self.deliveries_completed),
            (
                "Pedidos com ao menos uma perna concluida",
                self.orders_with_completed_leg,
            ),
            ("Ocorrencias registradas", self.occurrences_registered),
        )


class ManagementReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, requested: ManagementFilters) -> ManagementSummary:
        filters = validate_window(requested)
        trip_scope = select(Trip.id).join(LoadPlan, LoadPlan.id == Trip.load_plan_id)
        if filters.driver_id is not None:
            trip_scope = trip_scope.where(Trip.driver_id == filters.driver_id)
        if filters.truck_id is not None:
            trip_scope = trip_scope.where(LoadPlan.truck_id == filters.truck_id)

        trip_scope = trip_scope.subquery()

        def count(model, timestamp, *, distinct_column=None):
            expression = (
                func.count(distinct(distinct_column))
                if distinct_column is not None
                else func.count(model.id)
            )
            return int(
                self.db.scalar(
                    select(expression).where(
                        model.trip_id.in_(select(trip_scope.c.id))
                        if model is not Trip
                        else Trip.id.in_(select(trip_scope.c.id)),
                        timestamp >= filters.start,
                        timestamp < filters.end,
                    )
                )
                or 0
            )

        return ManagementSummary(
            start=filters.start,
            end=filters.end,
            trips_created=count(Trip, Trip.created_at),
            trips_started=count(Trip, Trip.started_at),
            trips_finished=count(Trip, Trip.finished_at),
            deliveries_completed=count(Delivery, Delivery.delivered_at),
            orders_with_completed_leg=count(
                Delivery, Delivery.delivered_at, distinct_column=Delivery.order_id
            ),
            occurrences_registered=count(Occurrence, Occurrence.created_at),
        )

    @staticmethod
    def csv_content(summary: ManagementSummary) -> str:
        stream = StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(("Indicador", "Total"))
        writer.writerows(summary.metrics())
        return stream.getvalue()

    @staticmethod
    def pdf_content(summary: ManagementSummary) -> bytes:
        return ReportService._build_pdf(
            "Relatorio gerencial",
            (
                ("Inicio UTC", summary.start.isoformat()),
                ("Fim exclusivo UTC", summary.end.isoformat()),
                (
                    "Contagem",
                    "Fatos operacionais; cada perna multi-caminhao conta uma vez",
                ),
            ),
            ("Indicador", "Total"),
            summary.metrics(),
        )
