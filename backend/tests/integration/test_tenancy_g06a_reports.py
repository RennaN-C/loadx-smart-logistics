"""Distribution metrics and paginated references retain the legacy tenant gate."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.load_planning.distribution_models import LoadDistribution
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID
from app.modules.reports.assistant_repository import AssistantMetricsRepository
from tests.integration.test_tenancy_g05c import _actor, _organization


@pytest.mark.parametrize("legacy_count", [0, 12])
def test_canceled_distribution_count_and_pages_exclude_other_organization(
    session_factory, legacy_count
):
    start = datetime(2026, 11, 19, tzinfo=UTC)
    end = start + timedelta(days=1)
    with session_factory() as db:
        other = _organization(db)
        actor = _actor(db, [LEGACY_ORGANIZATION_ID, other.id])
        expected_ids = []

        def add(organization_id, created_at, status="CANCELED"):
            identifier = uuid.uuid4()
            db.add(
                LoadDistribution(
                    id=identifier,
                    organization_id=organization_id,
                    created_by=actor.id,
                    status=status,
                    created_at=created_at,
                )
            )
            return identifier

        for _ in range(legacy_count):
            expected_ids.append(add(LEGACY_ORGANIZATION_ID, start))
        # The same global actor has memberships in both organizations. Foreign
        # rows sort first so filtering only after pagination cannot pass.
        for _ in range(11):
            add(other.id, start + timedelta(hours=1))
        add(LEGACY_ORGANIZATION_ID, start - timedelta(seconds=1))
        add(LEGACY_ORGANIZATION_ID, end)
        add(LEGACY_ORGANIZATION_ID, start, status="PROPOSED")
        db.flush()

        repository = AssistantMetricsRepository(db)
        assert repository.canceled(start, end) == {
            "currently_canceled_distributions_created_in_period": legacy_count
        }
        expected_ids.sort(reverse=True)
        for page in (1, 2, 3):
            rows = repository.canceled_items(start, end, page)
            assert [row.id for row in rows] == expected_ids[(page - 1) * 10 : page * 10]
            assert all(row.created_at == start for row in rows)
