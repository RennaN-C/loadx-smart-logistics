from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ApiError
from app.modules.reports.management_service import (
    ManagementFilters,
    ManagementReportService,
    ManagementSummary,
    validate_window,
)


def test_management_window_is_bounded_and_requires_aware_dates():
    start = datetime(2026, 10, 21, tzinfo=UTC)
    assert validate_window(
        ManagementFilters(start=start, end=start + timedelta(days=7))
    ).end == start + timedelta(days=7)
    for end in (
        start,
        start - timedelta(days=1),
        start + timedelta(days=94),
    ):
        with pytest.raises(ApiError):
            validate_window(ManagementFilters(start=start, end=end))
    with pytest.raises(ApiError):
        validate_window(
            ManagementFilters(
                start=start.replace(tzinfo=None),
                end=start + timedelta(days=1),
            )
        )


def test_management_export_preserves_counts_of_each_operational_fact():
    start = datetime(2026, 10, 21, tzinfo=UTC)
    summary = ManagementSummary(
        start=start,
        end=start + timedelta(days=1),
        trips_created=1,
        trips_started=2,
        trips_finished=3,
        deliveries_completed=4,
        orders_with_completed_leg=2,
        occurrences_registered=5,
        delivery_exceptions=6,
        trips_canceled=7,
        interruption_events=8,
    )
    exported = ManagementReportService.csv_content(summary)
    assert exported.startswith("Indicador,Total")
    assert "Pernas de entrega concluidas,4" in exported
    assert "Pedidos com ao menos uma perna concluida,2" in exported
    assert "Excecoes de entrega registradas,6" in exported
    assert "Viagens canceladas,7" in exported
    assert "Interrupcoes e retomadas,8" in exported
