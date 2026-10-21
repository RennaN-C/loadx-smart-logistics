"""Preflight policy remains conservative for physical and split-load operations."""

from app.modules.deliveries.cancellation_preflight import assess_cancellation


def test_scheduled_trip_without_loading_or_started_leg_is_candidate():
    assert (
        assess_cancellation(
            status="SCHEDULED",
            delivery_statuses=("PENDING", "PENDING"),
            has_distribution_part=False,
            loading_status=None,
        )
        == []
    )


def test_pending_loading_session_already_blocks_truck_release():
    assert assess_cancellation(
        status="SCHEDULED",
        delivery_statuses=("PENDING",),
        has_distribution_part=False,
        loading_status="PENDING",
    ) == ["LOADING_SESSION_EXISTS"]


def test_mixed_distribution_is_candidate_when_not_loaded():
    assert assess_cancellation(
        status="SCHEDULED",
        delivery_statuses=("PENDING",),
        has_distribution_part=True,
        loading_status=None,
    ) == []


def test_in_route_or_partial_completion_blocks_cancellation():
    assert assess_cancellation(
        status="IN_ROUTE",
        delivery_statuses=("DELIVERED", "IN_DELIVERY"),
        has_distribution_part=False,
        loading_status="FINISHED",
    ) == [
        "TRIP_ALREADY_STARTED_OR_FINISHED",
        "LOADING_SESSION_EXISTS",
        "DELIVERY_ALREADY_STARTED_OR_MISSING",
    ]


def test_missing_deliveries_are_ineligible():
    assert assess_cancellation(
        status="SCHEDULED",
        delivery_statuses=(),
        has_distribution_part=False,
        loading_status=None,
    ) == ["DELIVERY_ALREADY_STARTED_OR_MISSING"]
