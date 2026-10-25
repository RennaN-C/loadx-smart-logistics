from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from pypdf import PdfReader

from app.modules.reports.management_service import (
    ManagementReportService,
    ManagementSummary,
)
from app.modules.reports.pdf_renderer import build_pdf


def text_of(content: bytes) -> tuple[PdfReader, str]:
    reader = PdfReader(BytesIO(content))
    return reader, "\n".join(page.extract_text() for page in reader.pages)


@pytest.mark.parametrize(
    "title", ["Relatório de carregamento", "Relatório de viagem", "Relatório gerencial"]
)
def test_report_preserves_special_characters_and_full_identifiers(title):
    identifier = "00000000-0000-4000-8000-000000000001"
    _, text = text_of(
        build_pdf(
            title,
            (("Plano", identifier), ("Caminhão", "FIC1A23 · Modelo fictício")),
            ("Código", "Descrição"),
            [("PROD-01", "Café & açúcar <b>literal</b>\nSegunda linha")],
        )
    )
    assert title in text
    assert identifier in "".join(text.split())
    assert "Café & açúcar <b>literal</b>" in text
    assert "Segunda linha" in text
    assert "LOADX" in text
    assert "Página 1" in text
    assert "UTC" in text


def test_multipage_report_repeats_headers_and_keeps_every_volume():
    rows = [(f"ITEM-{i:03d}", f"Volume físico {i}", "CHECKED") for i in range(180)]
    reader, text = text_of(
        build_pdf(
            "Relatório de carregamento",
            (),
            ("Código", "Volume", "Conferência"),
            rows,
        )
    )
    assert len(reader.pages) > 2
    for i in range(180):
        assert f"ITEM-{i:03d}" in text
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        assert "LOADX" in page_text
        assert "Conferência" in page_text
        assert f"Página {index}" in page_text


def test_row_taller_than_a_page_is_split_without_losing_text():
    description = "Descrição extensa e rastreável. " * 400 + "MARCADOR-FINAL"
    reader, text = text_of(
        build_pdf(
            "Relatório de viagem",
            (),
            ("Tipo", "Descrição", "Data"),
            [("DELAY", description, "2026-10-25T12:00:00+00:00")],
            column_weights=(0.18, 0.55, 0.27),
        )
    )
    assert len(reader.pages) > 1
    assert text.count("rastreável.") == 400
    assert "MARCADOR-FINAL" in text


def test_empty_report_keeps_a_clear_empty_state():
    _, text = text_of(build_pdf("Relatório de viagem", (), ("Entrega", "Situação"), []))
    assert "Nenhum registro neste relatório." in text


def test_management_chart_preserves_zero_counts_and_distinct_operational_facts():
    start = datetime(2026, 10, 1, tzinfo=UTC)
    summary = ManagementSummary(
        start=start,
        end=start + timedelta(days=7),
        trips_created=0,
        trips_started=3,
        trips_finished=2,
        deliveries_completed=1000,
        orders_with_completed_leg=7,
        occurrences_registered=0,
        delivery_exceptions=1,
        trips_canceled=0,
        interruption_events=2,
    )
    reader, text = text_of(ManagementReportService.pdf_content(summary))
    assert len(reader.pages) == 1
    assert "1000" in text
    assert "Indicadores do período" in text
    assert "não devem ser somados" in text
    for label in (
        "Viagens criadas",
        "Viagens iniciadas",
        "Viagens finalizadas",
        "Pernas de entrega concluídas",
        "Pedidos com ao menos uma perna concluída",
        "Ocorrências registradas",
        "Exceções de entrega registradas",
        "Viagens canceladas",
        "Interrupções e retomadas",
    ):
        assert "".join(label.split()) in "".join(text.split())
    assert "2026-10-01T00:00:00+00:00" in text
    assert "2026-10-08T00:00:00+00:00" in text


def test_management_chart_handles_all_zero_counts():
    _, text = text_of(
        build_pdf(
            "Relatório gerencial",
            (),
            ("Indicador", "Total"),
            [("Viagens criadas", 0), ("Pernas concluídas", 0)],
            chart=True,
        )
    )
    assert "Viagens criadas" in text
    assert "Pernas concluídas" in text


def test_status_labels_are_localized_without_changing_identical_product_codes():
    _, text = text_of(
        build_pdf(
            "Relatório de carregamento",
            (("Status", "IN_PROGRESS"),),
            ("Código", "Conferência"),
            [("CHECKED", "CHECKED")],
        )
    )
    assert "Em andamento" in text
    assert "Conferido" in text
    assert "CHECKED" in text
