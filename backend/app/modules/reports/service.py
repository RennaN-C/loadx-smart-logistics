import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.deliveries.service import TripService
from app.modules.load_planning.reference_service import LoadPlanReferenceService
from app.modules.load_planning.service import LoadPlanningService
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.occurrences.service import OccurrenceService
from app.modules.reports.pdf_renderer import build_pdf
from app.modules.users.models import User


class ReportLoadingNotFoundError(Exception):
    pass


class ReportService:
    def __init__(self, db: Session) -> None:
        self.load_planning_service = LoadPlanningService(db)
        self.load_plan_reference_service = LoadPlanReferenceService(db)
        self.loading_reference_service = LoadingReferenceService(db)
        self.trip_service = TripService(db)
        self.occurrence_service = OccurrenceService(db)

    def build_loading_report(self, load_plan_id: uuid.UUID) -> bytes:
        plan = self.load_planning_service.get_load_plan(load_plan_id)
        loading = self.loading_reference_service.get_by_load_plan_id(load_plan_id)
        if loading is None:
            raise ReportLoadingNotFoundError
        checked_by_item = {
            item.load_plan_item_id: item.status for item in loading.items
        }
        rows = [
            (
                item.loading_sequence or "-",
                item.product_snapshot_code,
                f"{item.product_snapshot_name} ({item.order_item_id}, {item.volume_index})",
                checked_by_item.get(item.id, "PENDING"),
            )
            for item in sorted(
                plan.items,
                key=lambda value: (
                    value.loading_sequence or 10**9,
                    value.id.int,
                ),
            )
        ]
        metadata = (
            ("Plano", str(plan.id)),
            ("Caminhão", f"{plan.truck_snapshot_plate} - {plan.truck_snapshot_model}"),
            ("Status", loading.status),
            ("Início", self._format_datetime(loading.started_at)),
            ("Fim", self._format_datetime(loading.finished_at)),
        )
        metadata += tuple(self._distribution_metadata(plan.id))
        return self._build_pdf(
            "Relatório de carregamento",
            metadata,
            ("Sequência", "Código", "Volume", "Conferência"),
            rows,
            section_title="Sequência e conferência dos volumes",
            column_weights=(0.14, 0.16, 0.48, 0.22),
            metrics=(
                ("Volumes no plano", len(rows)),
                ("Conferidos", sum(row[3] == "CHECKED" for row in rows)),
                ("Conferência pendente", sum(row[3] == "PENDING" for row in rows)),
            ),
        )

    def build_trip_report(self, trip_id: uuid.UUID, *, current_user: User) -> bytes:
        trip = self.trip_service.get_trip(trip_id, current_user=current_user)
        plan = self.load_planning_service.get_load_plan(trip.load_plan_id)
        occurrences = self.occurrence_service.list_trip_occurrences(
            trip.id, current_user=current_user
        )
        delivery_rows = [
            (
                delivery.sequence,
                str(delivery.id),
                delivery.status,
                self._format_datetime(delivery.delivered_at),
            )
            for delivery in trip.deliveries
        ]
        occurrence_rows = [
            (
                occurrence.type,
                occurrence.description,
                self._format_datetime(occurrence.created_at),
            )
            for occurrence in occurrences
        ] or [("-", "Nenhuma ocorrência", "-")]
        metadata = (
            ("Viagem", str(trip.id)),
            ("Plano", str(plan.id)),
            ("Caminhão", f"{plan.truck_snapshot_plate} - {plan.truck_snapshot_model}"),
            ("Status", trip.status),
            ("Início", self._format_datetime(trip.started_at)),
            ("Fim", self._format_datetime(trip.finished_at)),
        )
        metadata += tuple(self._distribution_metadata(plan.id))
        volume_rows = [
            (str(item.order_item_id), item.volume_index, str(item.order_id))
            for item in sorted(
                plan.items, key=lambda item: (item.order_item_id.int, item.volume_index)
            )
            if item.placed
        ]
        return self._build_pdf(
            "Relatório de viagem",
            metadata,
            ("Seq.", "Entrega", "Status", "Data"),
            delivery_rows,
            secondary_title="Ocorrências",
            secondary_headers=("Tipo", "Descrição", "Data"),
            secondary_rows=occurrence_rows,
            volume_rows=volume_rows,
            section_title="Entregas da viagem",
            column_weights=(0.10, 0.39, 0.22, 0.29),
            metrics=(
                ("Entregas da viagem", len(delivery_rows)),
                (
                    "Entregas concluídas",
                    sum(row[2] == "DELIVERED" for row in delivery_rows),
                ),
                ("Ocorrências", len(occurrences)),
            ),
        )

    def _distribution_metadata(self, load_plan_id: uuid.UUID) -> list[tuple[str, str]]:
        part = self.load_plan_reference_service.get_distribution_part_for_plan(
            load_plan_id
        )
        if part is None:
            return []
        return [
            ("Distribuição", str(part.distribution_id)),
            ("Parte", str(part.part_id)),
            ("Volumes da parte", str(len(part.volumes))),
        ]

    # Shared renderer also serves the management export; keep this internal
    # entry point for callers while presentation stays independent of services.
    _build_pdf = staticmethod(build_pdf)

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        if value is None:
            return "-"
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
