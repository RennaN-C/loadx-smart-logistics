"""PostgreSQL 16 migration guards and lossless legacy recovery backfill."""

import uuid
from datetime import UTC, datetime
from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.modules.customers.models import Customer
from app.modules.load_planning.distribution_models import (
    LoadDistribution,
    LoadDistributionOrder,
)
from app.modules.orders.models import Order
from app.modules.organizations.models import (
    LEGACY_ORGANIZATION_ID,
    Organization,
    OrganizationMembership,
)
from app.modules.users.models import User

migration = import_module(
    "migrations.versions.20261119_0045_scope_optimization_requests"
)


def _run(db, operation):
    with Operations.context(MigrationContext.configure(db.connection())):
        getattr(migration, operation)()


def _organization(db):
    organization = Organization(
        legal_name="Empresa fictícia G05-C", display_name="G05-C", status="PENDING"
    )
    db.add(organization)
    db.flush()
    return organization.id


def _historical_request(
    db, owner_id=LEGACY_ORGANIZATION_ID, *, member=True, parent=True
):
    user = User(
        name="Ator fictício",
        email=f"{uuid.uuid4().hex}@example.test",
        password_hash="unused-test-hash",
        role="CHECKER",
        active=True,
    )
    db.add(user)
    db.flush()
    if member:
        db.add(
            OrganizationMembership(
                organization_id=LEGACY_ORGANIZATION_ID,
                user_id=user.id,
                role="CHECKER",
                status="ACTIVE",
            )
        )
    distribution = LoadDistribution(status="CANCELED", created_by=user.id)
    db.add(distribution)
    db.flush()
    if parent:
        customer = Customer(
            organization_id=owner_id,
            name="Cliente fictício G05-C",
            document=f"{uuid.uuid4().int % 10**14:014d}",
            address="Rua de Teste",
            city="Curitiba",
            state="PR",
        )
        db.add(customer)
        db.flush()
        order = Order(
            organization_id=owner_id,
            customer_id=customer.id,
            status="DRAFT",
            priority="NORMAL",
            delivery_address="Rua de Teste",
        )
        db.add(order)
        db.flush()
        db.add(
            LoadDistributionOrder(
                distribution_id=distribution.id,
                order_id=order.id,
                active=False,
            )
        )
        db.flush()
    values = {
        "user": user.id,
        "key": uuid.uuid4(),
        "distribution": distribution.id,
        "hash": "a" * 64,
        "created": datetime(2026, 11, 14, 12, 30, tzinfo=UTC),
    }
    db.execute(
        text(
            "INSERT INTO optimization_requests "
            "(user_id, request_key, distribution_id, payload_hash, created_at) "
            "VALUES (:user, :key, :distribution, :hash, :created)"
        ),
        values,
    )
    return values


def _rows(db):
    return db.execute(
        text(
            "SELECT user_id, request_key, distribution_id, payload_hash, created_at "
            "FROM optimization_requests ORDER BY user_id, request_key"
        )
    ).all()


def test_upgrade_and_downgrade_preserve_historical_requests(session_factory):
    with session_factory() as db:
        _run(db, "downgrade")
        _historical_request(db)
        _historical_request(db)
        before = _rows(db)
        _run(db, "upgrade")
        assert _rows(db) == before
        assert db.execute(
            text("SELECT DISTINCT organization_id FROM optimization_requests")
        ).scalars().all() == [LEGACY_ORGANIZATION_ID]
        columns = inspect(db.connection()).get_columns("optimization_requests")
        organization = next(c for c in columns if c["name"] == "organization_id")
        assert organization["nullable"] is False
        assert organization["default"] is None
        assert inspect(db.connection()).get_pk_constraint("optimization_requests")[
            "constrained_columns"
        ] == ["organization_id", "user_id", "request_key"]
        _run(db, "downgrade")
        assert _rows(db) == before
        _run(db, "upgrade")
        assert _rows(db) == before


@pytest.mark.parametrize(
    "invalid", ["foreign", "mixed", "missing_membership", "no_parents"]
)
def test_upgrade_refuses_unproven_or_cross_organization_ownership(
    session_factory, invalid
):
    with session_factory() as db:
        _run(db, "downgrade")
        other = _organization(db)
        values = _historical_request(
            db,
            owner_id=other
            if invalid in {"foreign", "mixed"}
            else LEGACY_ORGANIZATION_ID,
            member=invalid != "missing_membership",
            parent=invalid != "no_parents",
        )
        if invalid == "mixed":
            second = _historical_request(db)
            db.execute(
                text(
                    "UPDATE load_distribution_orders SET distribution_id=:target "
                    "WHERE distribution_id=:source"
                ),
                {"target": values["distribution"], "source": second["distribution"]},
            )
            db.execute(
                text("DELETE FROM optimization_requests WHERE request_key=:key"),
                {"key": second["key"]},
            )
        before = _rows(db)
        with (
            pytest.raises(DBAPIError, match="G05-C upgrade refused"),
            db.begin_nested(),
        ):
            _run(db, "upgrade")
        assert _rows(db) == before
        assert "organization_id" not in {
            c["name"]
            for c in inspect(db.connection()).get_columns("optimization_requests")
        }


def test_downgrade_refuses_foreign_request_and_preserves_schema(session_factory):
    with session_factory() as db:
        _run(db, "downgrade")
        values = _historical_request(db)
        _run(db, "upgrade")
        other = _organization(db)
        db.add(
            OrganizationMembership(
                organization_id=other,
                user_id=values["user"],
                role="CHECKER",
                status="ACTIVE",
            )
        )
        db.flush()
        db.execute(
            text(
                "UPDATE optimization_requests SET organization_id=:org WHERE request_key=:key"
            ),
            {"org": other, "key": values["key"]},
        )
        before = _rows(db)
        with (
            pytest.raises(DBAPIError, match="G05-C downgrade refused"),
            db.begin_nested(),
        ):
            _run(db, "downgrade")
        assert _rows(db) == before
        assert (
            db.execute(
                text(
                    "SELECT organization_id FROM optimization_requests WHERE request_key=:key"
                ),
                {"key": values["key"]},
            ).scalar_one()
            == other
        )


def test_organization_and_membership_are_required_without_default(session_factory):
    with session_factory() as db:
        _run(db, "downgrade")
        values = _historical_request(db)
        _run(db, "upgrade")
        other = _organization(db)
        with pytest.raises(IntegrityError) as exc, db.begin_nested():
            db.execute(
                text(
                    "UPDATE optimization_requests SET organization_id=:org WHERE request_key=:key"
                ),
                {"org": other, "key": values["key"]},
            )
        assert exc.value.orig.sqlstate == "23503"
        assert (
            exc.value.orig.diag.constraint_name
            == "fk_optimization_requests__organization_user"
        )
        with pytest.raises(IntegrityError) as exc, db.begin_nested():
            db.execute(
                text(
                    "UPDATE optimization_requests SET organization_id=NULL WHERE request_key=:key"
                ),
                {"key": values["key"]},
            )
        assert exc.value.orig.sqlstate == "23502"


def _attach_plan(db, distribution_id, organization_id):
    from app.modules.load_planning.distribution_models import LoadDistributionPart
    from app.modules.load_planning.models import LoadPlan
    from app.modules.trucks.models import Truck

    truck = Truck(
        organization_id=organization_id,
        plate="G05C123",
        model="Frota fictícia",
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=100,
    )
    db.add(truck)
    db.flush()
    plan = LoadPlan(
        organization_id=organization_id,
        truck_id=truck.id,
        status="REJECTED",
        truck_snapshot_plate=truck.plate,
        truck_snapshot_model=truck.model,
        truck_snapshot_internal_width_cm=100,
        truck_snapshot_internal_height_cm=100,
        truck_snapshot_internal_length_cm=100,
        truck_snapshot_max_weight_kg=100,
        internal_volume_cm3=1_000_000,
        used_volume_cm3=0,
        occupancy_percent=0,
        total_weight_kg=0,
        loaded_count=0,
        unloaded_count=1,
        algorithm_version="heuristic-v1",
    )
    db.add(plan)
    db.flush()
    part = LoadDistributionPart(
        distribution_id=distribution_id,
        load_plan_id=plan.id,
        status="CANCELED",
    )
    db.add(part)
    db.flush()
    return part


def test_upgrade_refuses_foreign_plan_even_with_legacy_orders(session_factory):
    with session_factory() as db:
        _run(db, "downgrade")
        other = _organization(db)
        values = _historical_request(db)
        part = _attach_plan(db, values["distribution"], other)
        before = _rows(db)
        with (
            pytest.raises(DBAPIError, match="G05-C upgrade refused"),
            db.begin_nested(),
        ):
            _run(db, "upgrade")
        assert _rows(db) == before
        assert (
            db.execute(
                text("SELECT load_plan_id FROM load_distribution_parts WHERE id=:id"),
                {"id": part.id},
            ).scalar_one()
            == part.load_plan_id
        )
        assert "organization_id" not in {
            c["name"]
            for c in inspect(db.connection()).get_columns("optimization_requests")
        }


@pytest.mark.parametrize("foreign", [False, True])
def test_upgrade_reconciles_full_volume_graph_and_preserves_its_identity(
    session_factory,
    foreign,
):
    from app.modules.load_planning.distribution_models import LoadDistributionVolume
    from app.modules.orders.models import OrderItem
    from app.modules.products.models import Product

    with session_factory() as db:
        _run(db, "downgrade")
        organization_id = _organization(db) if foreign else LEGACY_ORGANIZATION_ID
        values = _historical_request(db, owner_id=organization_id)
        part = _attach_plan(db, values["distribution"], organization_id)
        order_id = db.execute(
            text(
                "SELECT order_id FROM load_distribution_orders WHERE distribution_id=:id"
            ),
            {"id": values["distribution"]},
        ).scalar_one()
        product = Product(
            organization_id=organization_id,
            code="G05C-MIGRATION",
            name="Volume fictício",
            width_cm=10,
            height_cm=10,
            length_cm=10,
            weight_kg=1,
            fragile=False,
            stackable=True,
            rotation_allowed=True,
        )
        db.add(product)
        db.flush()
        item = OrderItem(
            organization_id=organization_id,
            order_id=order_id,
            product_id=product.id,
            quantity=1,
            delivery_sequence=1,
        )
        db.add(item)
        db.flush()
        volume = LoadDistributionVolume(
            distribution_id=values["distribution"],
            order_item_id=item.id,
            volume_index=1,
            order_id=order_id,
            product_id=product.id,
            snapshot_quantity=1,
            part_id=part.id,
            active=False,
        )
        db.add(volume)
        db.flush()
        before = _rows(db)
        graph_sql = text(
            "SELECT distribution_id, order_item_id, volume_index, order_id, "
            "product_id, snapshot_quantity, part_id, active "
            "FROM load_distribution_volumes WHERE distribution_id=:id"
        )
        graph_before = db.execute(graph_sql, {"id": values["distribution"]}).all()
        if foreign:
            with (
                pytest.raises(DBAPIError, match="G05-C upgrade refused"),
                db.begin_nested(),
            ):
                _run(db, "upgrade")
            assert _rows(db) == before
            assert (
                db.execute(graph_sql, {"id": values["distribution"]}).all()
                == graph_before
            )
            return
        _run(db, "upgrade")
        assert _rows(db) == before
        assert (
            db.execute(graph_sql, {"id": values["distribution"]}).all() == graph_before
        )
        _run(db, "downgrade")
        assert _rows(db) == before
        assert (
            db.execute(graph_sql, {"id": values["distribution"]}).all() == graph_before
        )
