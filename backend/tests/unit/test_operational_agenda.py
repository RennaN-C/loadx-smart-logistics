from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ApiError
from app.modules.operational_agenda.service import AgendaFilters, validate_window


def test_agenda_period_limited_to_one_week():
    start = datetime(2026, 10, 21, tzinfo=UTC)
    valid = validate_window(AgendaFilters(start, start + timedelta(days=7)))
    assert valid.end == start + timedelta(days=7)
    with pytest.raises(ApiError):
        validate_window(AgendaFilters(start, start + timedelta(days=8)))
    with pytest.raises(ApiError):
        validate_window(AgendaFilters(start, start))


def test_agenda_requires_timezone():
    start = datetime(2026, 10, 21, tzinfo=UTC)
    with pytest.raises(ApiError):
        validate_window(
            AgendaFilters(start.replace(tzinfo=None), start + timedelta(days=1))
        )
