import uuid

import pytest
from pydantic import ValidationError

from app.modules.loading.schemas import LoadingItemScan, LoadingSessionItemRead
from app.modules.loading.service import (
    LoadingItemAlreadyCheckedError,
    LoadingService,
    LoadingStatusTransitionError,
)
from tests.unit.test_loading_service import SQLITE_TABLES, seed_plan

__all__ = ("SQLITE_TABLES",)


@pytest.mark.parametrize(
    "code",
    [
        "",
        "not-a-code",
        str(uuid.uuid4()),
        "loadx:loading-item:" + "z" * 36,
        "loadx:loading-item:" + str(uuid.uuid4()).upper(),
        " loadx:loading-item:" + str(uuid.uuid4()),
    ],
)
def test_scan_rejects_invalid_code(code):
    with pytest.raises(ValidationError):
        LoadingItemScan(code=code)


def test_code_round_trip_and_extra_fields():
    item_id = uuid.uuid4()
    item = LoadingSessionItemRead(
        id=item_id, load_plan_item_id=uuid.uuid4(), status="PENDING"
    )
    assert LoadingItemScan(code=item.model_dump()["code"]).item_id == item_id
    with pytest.raises(ValidationError):
        LoadingItemScan(code=item.code, status="CHECKED")


def test_scan_reuses_checklist_and_rejects_duplicate(db_session):
    service = LoadingService(db_session)
    loading = service.create_session(seed_plan(db_session).id)
    item_id = loading.items[0].id
    with pytest.raises(LoadingStatusTransitionError):
        service.scan_item(loading.id, item_id)
    assert all(item.status == "PENDING" for item in loading.items)
    service.change_status(loading.id, "IN_PROGRESS")
    result = service.scan_item(loading.id, item_id)
    assert sum(item.status == "CHECKED" for item in result.items) == 1
    with pytest.raises(LoadingItemAlreadyCheckedError):
        service.scan_item(loading.id, item_id)
    # Manual operation retains its existing idempotent contract.
    assert service.change_item_status(loading.id, item_id, "CHECKED").id == loading.id
