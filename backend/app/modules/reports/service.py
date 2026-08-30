import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab import __file__ as reportlab_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.modules.deliveries.service import TripService
from app.modules.load_planning.service import LoadPlanningService
from app.modules.loading.reference_service import LoadingReferenceService
from app.modules.occurrences.service import OccurrenceService
from app.modules.users.models import User


class ReportLoadingNotFoundError(Exception):
    pass


class ReportService:
    def __init__(self, db: Session) -> None:
        self.load_planning_service = LoadPlanningService(db)
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
                f"{item.product_snapshot_name} #{item.volume_index}",
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
        return self._build_pdf(
            "Relatório de carregamento",
            metadata,
            ("Sequência", "Código", "Volume", "Conferência"),
            rows,
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
            ("Caminhão", f"{plan.truck_snapshot_plate} - {plan.truck_snapshot_model}"),
            ("Status", trip.status),
            ("Início", self._format_datetime(trip.started_at)),
            ("Fim", self._format_datetime(trip.finished_at)),
        )
        return self._build_pdf(
            "Relatório de viagem",
            metadata,
            ("Sequência", "Entrega", "Status", "Data"),
            delivery_rows,
            secondary_title="Ocorrências",
            secondary_headers=("Tipo", "Descrição", "Data"),
            secondary_rows=occurrence_rows,
        )

    @staticmethod
    def _build_pdf(
        title: str,
        metadata: Iterable[tuple[str, str]],
        headers: tuple[str, ...],
        rows: Iterable[tuple[object, ...]],
        *,
        secondary_title: str | None = None,
        secondary_headers: tuple[str, ...] = (),
        secondary_rows: Iterable[tuple[object, ...]] = (),
    ) -> bytes:
        stream = BytesIO()
        document = SimpleDocTemplate(
            stream,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=title,
        )
        ReportService._register_fonts()
        styles = getSampleStyleSheet()
        for style_name in ("BodyText", "Title", "Heading2"):
            styles[style_name].fontName = "LoadX"
        styles["Title"].fontName = "LoadX-Bold"
        styles["Heading2"].fontName = "LoadX-Bold"
        story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 5 * mm)]
        for label, value in metadata:
            story.append(
                Paragraph(
                    f"{escape(label)}: {escape(value)}",
                    styles["BodyText"],
                )
            )
        story.extend((Spacer(1, 7 * mm), Paragraph("Detalhes", styles["Heading2"])))
        story.append(ReportService._table(headers, rows))
        if secondary_title is not None:
            story.extend(
                (
                    Spacer(1, 7 * mm),
                    Paragraph(escape(secondary_title), styles["Heading2"]),
                    ReportService._table(secondary_headers, secondary_rows),
                )
            )
        document.build(story)
        return stream.getvalue()

    @staticmethod
    def _table(headers: tuple[str, ...], rows: Iterable[tuple[object, ...]]) -> Table:
        ReportService._register_fonts()
        body_style = ParagraphStyle("LoadXBody", fontName="LoadX", fontSize=9)
        header_style = ParagraphStyle(
            "LoadXHeader",
            fontName="LoadX-Bold",
            fontSize=9,
            textColor=colors.white,
        )
        data = [[Paragraph(escape(str(value)), header_style) for value in headers]]
        data.extend(
            [
                [Paragraph(escape(str(value)), body_style) for value in row]
                for row in rows
            ]
        )
        table = Table(
            data,
            colWidths=[178 * mm / len(headers)] * len(headers),
            repeatRows=1,
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AAB7C4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    @staticmethod
    def _register_fonts() -> None:
        if "LoadX" in pdfmetrics.getRegisteredFontNames():
            return
        fonts_dir = Path(reportlab_file).resolve().parent / "fonts"
        pdfmetrics.registerFont(TTFont("LoadX", str(fonts_dir / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("LoadX-Bold", str(fonts_dir / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily(
            "LoadX",
            normal="LoadX",
            bold="LoadX-Bold",
            italic="LoadX",
            boldItalic="LoadX-Bold",
        )

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        if value is None:
            return "-"
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
