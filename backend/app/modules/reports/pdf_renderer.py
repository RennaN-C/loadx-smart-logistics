"""Shared presentation for operational PDFs; no data access or business rules."""

from collections.abc import Iterable
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab import __file__ as reportlab_file
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    CondPageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#102938")
AMBER = colors.HexColor("#F2AE32")
INK = colors.HexColor("#193347")
MUTED = colors.HexColor("#526878")
LINE = colors.HexColor("#DAE3EA")
PAPER = colors.HexColor("#F3F6F9")
WIDTH = A4[0] - 32 * mm
LABELS = {
    "PENDING": "Pendente",
    "CHECKED": "Conferido",
    "IN_PROGRESS": "Em andamento",
    "FINISHED": "Finalizada",
    "SCHEDULED": "Programada",
    "IN_ROUTE": "Em rota",
    "IN_DELIVERY": "Em entrega",
    "DELIVERED": "Entregue",
    "CANCELED": "Cancelada",
    "DAMAGED_PRODUCT": "Produto avariado",
    "CUSTOMER_ABSENT": "Cliente ausente",
    "WRONG_ADDRESS": "Endereço incorreto",
    "REFUSED_PRODUCT": "Produto recusado",
    "MISSING_VOLUME": "Volume ausente",
    "DELAY": "Atraso",
    "VEHICLE_PROBLEM": "Problema no veículo",
    "LOADING_PROBLEM": "Problema no carregamento",
}


def _register_fonts() -> None:
    if "LoadX" in pdfmetrics.getRegisteredFontNames():
        return
    fonts = Path(reportlab_file).resolve().parent / "fonts"
    pdfmetrics.registerFont(TTFont("LoadX", str(fonts / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("LoadX-Bold", str(fonts / "VeraBd.ttf")))
    pdfmetrics.registerFontFamily(
        "LoadX",
        normal="LoadX",
        bold="LoadX-Bold",
        italic="LoadX",
        boldItalic="LoadX-Bold",
    )


def _paragraph(value: object, *, size: float = 8, bold: bool = False) -> Paragraph:
    return Paragraph(
        escape(str(value)).replace("\n", "<br/>"),
        ParagraphStyle(
            "ReportText",
            fontName="LoadX-Bold" if bold else "LoadX",
            fontSize=size,
            leading=size * 1.5,
            textColor=INK,
            spaceAfter=0,
        ),
    )


def _section(title: str) -> Paragraph:
    return Paragraph(
        escape(title),
        ParagraphStyle(
            "ReportSection",
            fontName="LoadX-Bold",
            fontSize=12,
            leading=17,
            textColor=INK,
            spaceBefore=19,
            spaceAfter=10,
            keepWithNext=False,
        ),
    )


def _cell(header: str, value: object) -> Drawing | Paragraph:
    if isinstance(value, Drawing):
        return value
    if header in {"Status", "Conferência", "Tipo"}:
        value = LABELS.get(str(value), value)
    return _paragraph(value)


def _table(
    headers: tuple[str, ...],
    rows: Iterable[tuple[object, ...]],
    weights: tuple[float, ...] | None = None,
    *,
    compact: bool = False,
) -> Table:
    weights = weights or tuple(1 for _ in headers)
    widths = [WIDTH * weight / sum(weights) for weight in weights]
    header_style = ParagraphStyle(
        "ReportColumn",
        fontName="LoadX-Bold",
        fontSize=7.5,
        leading=11,
        textColor=colors.white,
    )
    data = [[Paragraph(escape(label), header_style) for label in headers]]
    body = [
        [_cell(headers[index], value) for index, value in enumerate(row)]
        for row in rows
    ]
    data.extend(
        body
        or [
            [_paragraph("Nenhum registro neste relatório.")] + [""] * (len(headers) - 1)
        ]
    )
    table = Table(data, colWidths=widths, repeatRows=1, splitInRow=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
        ("LINEBELOW", (0, 0), (-1, 0), 2, AMBER),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7 if compact else 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7 if compact else 10),
    ]
    if not body:
        commands.append(("SPAN", (0, 1), (-1, 1)))
    table.setStyle(TableStyle(commands))
    return table


def _metadata(rows: Iterable[tuple[str, str]]) -> Table:
    cells = []
    for label, value in rows:
        cells.append(
            [
                _paragraph(label.upper(), size=6.5, bold=True),
                Spacer(1, 3),
                _paragraph(
                    LABELS.get(value, value) if label == "Status" else value, size=8
                ),
            ]
        )
    if len(cells) % 2:
        cells.append("")
    table = Table(
        [cells[i : i + 2] for i in range(0, len(cells), 2)],
        colWidths=[WIDTH / 2] * 2,
        splitInRow=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.white),
            ]
        )
    )
    return table


def _metrics(metrics: tuple[tuple[str, object], ...]) -> Table:
    cells = []
    for label, value in metrics:
        cells.append(
            [
                _paragraph(value, size=22, bold=True),
                Spacer(1, 4),
                _paragraph(label, size=8),
            ]
        )
    table = Table([cells], colWidths=[WIDTH / len(cells)] * len(cells))
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEABOVE", (0, 0), (-1, -1), 2, AMBER),
                ("LINEAFTER", (0, 0), (-2, 0), 0.5, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return table


def _page_chrome(canvas: Canvas, document: SimpleDocTemplate, *, issued: str) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 28 * mm, width, 28 * mm, fill=1, stroke=0)
    canvas.setFillColor(AMBER)
    for x, bar_height in ((16, 5), (19, 9), (22, 13)):
        canvas.rect(x * mm, height - 19 * mm, 1.7 * mm, bar_height, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("LoadX-Bold", 15)
    canvas.drawString(28 * mm, height - 19 * mm, "LOADX")
    canvas.setFont("LoadX", 7)
    canvas.drawRightString(
        width - 16 * mm, height - 18 * mm, "INTELIGÊNCIA NA OPERAÇÃO"
    )
    canvas.setStrokeColor(AMBER)
    canvas.setLineWidth(2)
    canvas.line(16 * mm, height - 28 * mm, 40 * mm, height - 28 * mm)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(16 * mm, 17 * mm, width - 16 * mm, 17 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("LoadX", 6.5)
    canvas.drawString(16 * mm, 12 * mm, f"Emitido em {issued} UTC · LoadX")
    canvas.drawRightString(width - 16 * mm, 12 * mm, f"Página {document.page}")
    canvas.restoreState()


def build_pdf(
    title: str,
    metadata: Iterable[tuple[str, str]],
    headers: tuple[str, ...],
    rows: Iterable[tuple[object, ...]],
    *,
    secondary_title: str | None = None,
    secondary_headers: tuple[str, ...] = (),
    secondary_rows: Iterable[tuple[object, ...]] = (),
    volume_rows: Iterable[tuple[object, ...]] = (),
    metrics: tuple[tuple[str, object], ...] = (),
    section_title: str = "Detalhes",
    column_weights: tuple[float, ...] | None = None,
    chart: bool = False,
) -> bytes:
    _register_fonts()
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=37 * mm,
        bottomMargin=23 * mm,
        title=title,
        author="LoadX",
        subject="Relatório operacional",
    )
    story = [
        Paragraph(
            escape(title),
            ParagraphStyle(
                "ReportTitle",
                fontName="LoadX-Bold",
                fontSize=23,
                leading=29,
                textColor=NAVY,
                spaceAfter=7,
            ),
        ),
        _paragraph("Visão operacional · Dados persistidos no sistema", size=8),
        Spacer(1, 18),
    ]
    metadata_rows = list(metadata)
    if metadata_rows:
        story.append(_metadata(metadata_rows))
    if metrics:
        story.extend([Spacer(1, 18), _metrics(metrics)])
    story.extend([CondPageBreak(110), _section(section_title)])
    data = list(rows)
    if chart:
        maximum = max((int(row[1]) for row in data), default=0)
        chart_rows = []
        for label, total in data:
            drawing = Drawing(120, 16)
            drawing.add(Rect(0, 4, 120, 7, fillColor=LINE, strokeColor=None))
            if maximum:
                drawing.add(
                    Rect(
                        0,
                        4,
                        120 * int(total) / maximum,
                        7,
                        fillColor=AMBER,
                        strokeColor=None,
                    )
                )
            chart_rows.append((label, drawing, total))
        story.append(
            _table(
                (headers[0], "Volume no período", headers[1]),
                chart_rows,
                (0.57, 0.30, 0.13),
                compact=True,
            )
        )
        story.extend(
            [
                Spacer(1, 9),
                _paragraph(
                    "Escala relativa ao maior total. Indicadores representam fatos distintos e não devem ser somados.",
                    size=7,
                ),
            ]
        )
    else:
        story.append(_table(headers, data, column_weights))
    if secondary_title is not None:
        story.extend(
            [
                CondPageBreak(110),
                _section(secondary_title),
                _table(secondary_headers, secondary_rows, (0.20, 0.52, 0.28)),
            ]
        )
    volumes = list(volume_rows)
    if volumes:
        story.extend(
            [
                CondPageBreak(110),
                _section("Volumes transportados"),
                _table(
                    ("Item do pedido", "Índice do volume", "Pedido"),
                    volumes,
                    (0.44, 0.12, 0.44),
                ),
            ]
        )
    issued = datetime.now(UTC).strftime("%d/%m/%Y %H:%M")

    def chrome(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        _page_chrome(canvas, doc, issued=issued)

    document.build(story, onFirstPage=chrome, onLaterPages=chrome)
    return stream.getvalue()
