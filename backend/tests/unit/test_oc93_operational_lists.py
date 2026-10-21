"""OC93 listing endpoints enforce pagination and status contracts."""

import uuid

from app.core.pagination import PaginationParams
from app.modules.deliveries.models import Delivery, Trip
from app.modules.deliveries.operational_lists_router import (
    DeliveryStatus,
    LoadingListRead,
    LoadingStatus,
)
from app.modules.loading.models import LoadingSession


def test_operational_index_contracts():
    assert Trip.__tablename__ == "trips"
    assert Delivery.__tablename__ == "deliveries"
    assert LoadingSession.__tablename__ == "loading_sessions"
    assert PaginationParams(page=2, page_size=20, sort_order="desc").offset == 20
    assert "DELIVERED" in DeliveryStatus.__args__
    assert "FINISHED" in LoadingStatus.__args__


def test_loading_projection_does_not_include_personal_data():
    row = LoadingListRead(
        id=uuid.uuid4(),
        load_plan_id=uuid.uuid4(),
        status="PENDING",
        started_at=None,
        finished_at=None,
    )
    assert "driver_id" not in row.model_dump()
    assert "customer" not in str(row.model_dump())
