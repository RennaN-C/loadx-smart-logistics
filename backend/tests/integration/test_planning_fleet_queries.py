"""Fleet preflight must keep SQL bounded without weakening truck eligibility."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import event

from app.modules.load_planning.distribution_schemas import DistributionNeedRequest
from app.modules.load_planning.distribution_service import LoadDistributionService
from app.modules.trucks.models import (
    Truck,
    TruckDocument,
    TruckDocumentPolicy,
    TruckMaintenance,
)
from app.modules.trucks.service import TruckService
from tests.integration.test_load_planning_api import seed_planning_scenario


def add_trucks(db, count):
    records = [
        Truck(
            plate=uuid.uuid4().hex[:7].upper(),
            model="Frota fictícia arquivada",
            internal_width_cm=100,
            internal_height_cm=100,
            internal_length_cm=100,
            max_weight_kg=1000,
            active=False,
        )
        for _ in range(count)
    ]
    db.add_all(records)
    db.commit()
    return records


def test_preflight_query_count_does_not_grow_with_archived_fleet(session_factory):
    scenario = seed_planning_scenario(session_factory, quantity=1)
    with session_factory() as db:
        add_trucks(db, 10)
        engine = db.get_bind()
        statements = []

        def count(_connection, _cursor, statement, *_args):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", count)
        try:
            service = LoadDistributionService(db)
            request = DistributionNeedRequest(order_ids=[scenario.order_id])
            first = service.preflight(request)
            first_count = len(statements)
            add_trucks(db, 90)
            statements.clear()
            second = service.preflight(request)
            second_count = len(statements)
        finally:
            event.remove(engine, "before_cursor_execute", count)
        assert first_count == second_count
        assert first_count <= 15
        assert [t.id for t in first.eligible_trucks] == [scenario.truck_id]
        assert [t.id for t in second.eligible_trucks] == [scenario.truck_id]
        assert len(second.ineligible_trucks) == len(first.ineligible_trucks) + 90
        assert all(t.reason == "INACTIVE" for t in second.ineligible_trucks)


def test_batch_conflicts_keep_document_and_maintenance_boundaries(session_factory):
    now = datetime.now(UTC)
    with session_factory() as db:
        expired, future, valid, maintained, ended, closed = add_trucks(db, 6)
        for truck in (expired, future, valid):
            db.add(TruckDocumentPolicy(truck_id=truck.id, kind="CRLV", required=True))
        for truck, issued, expires in (
            (expired, now - timedelta(days=2), now),
            (future, now + timedelta(seconds=1), now + timedelta(days=2)),
            (valid, now, now + timedelta(days=2)),
        ):
            db.add(
                TruckDocument(
                    truck_id=truck.id,
                    kind="CRLV",
                    reference="FICTICIO",
                    issued_at=issued,
                    expires_at=expires,
                )
            )
        for truck, ends_at, closed_at in (
            (maintained, None, None),
            (ended, now, None),
            (closed, None, now),
        ):
            db.add(
                TruckMaintenance(
                    truck_id=truck.id,
                    kind="PREVENTIVE",
                    starts_at=now - timedelta(days=1),
                    ends_at=ends_at,
                    closed_at=closed_at,
                    description="Revisão fictícia",
                )
            )
        db.commit()
        conflicts = TruckService(db).get_operational_conflicts(at=now)
        assert conflicts.documents == {expired.id, future.id}
        assert conflicts.maintenance == {maintained.id}
        assert conflicts.operations == set()
