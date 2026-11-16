"""G05-B PostgreSQL 16 ownership of planning order links and volume provenance."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.integrity import get_integrity_constraint_name
from app.modules.customers.models import Customer
from app.modules.load_planning.models import LoadPlan, LoadPlanItem, LoadPlanOrder
from app.modules.load_planning.repository import LoadPlanRepository
from app.modules.orders.models import Order, OrderItem
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID, Organization
from app.modules.products.models import Product
from app.modules.trucks.models import Truck


def _other_organization(db):
    org = Organization(
        legal_name="Transportadora fictícia G05-B",
        display_name="Transportadora G05-B",
        status="PENDING",
    )
    db.add(org)
    db.flush()
    return org


def _truck(db, organization_id, plate):
    row = Truck(
        organization_id=organization_id,
        plate=plate,
        model="Frota fictícia",
        internal_width_cm=100,
        internal_height_cm=100,
        internal_length_cm=100,
        max_weight_kg=Decimal("100.00"),
    )
    db.add(row)
    db.flush()
    return row


def _order_and_item(db, organization_id):
    customer = Customer(
        organization_id=organization_id,
        name="Cliente fictício G05-B",
        document=f"{uuid.uuid4().int % 10**14:014d}",
        address="Rua de Teste",
        city="Curitiba",
        state="PR",
    )
    product = Product(
        organization_id=organization_id,
        code=f"G05B-{uuid.uuid4().hex[:12].upper()}",
        name="Volume fictício",
        width_cm=10,
        height_cm=20,
        length_cm=30,
        weight_kg=Decimal("3.250"),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )
    db.add_all([customer, product])
    db.flush()
    order = Order(
        organization_id=organization_id,
        customer_id=customer.id,
        status="DRAFT",
        priority="NORMAL",
        delivery_address="Rua de Teste",
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        organization_id=organization_id,
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        delivery_sequence=1,
    )
    db.add(item)
    db.flush()
    return order, item, product


def _plan(org_id, truck_id):
    return LoadPlan(
        organization_id=org_id,
        truck_id=truck_id,
        status="REJECTED",
        truck_snapshot_plate="G05B123",
        truck_snapshot_model="Frota fictícia",
        truck_snapshot_internal_width_cm=100,
        truck_snapshot_internal_height_cm=100,
        truck_snapshot_internal_length_cm=100,
        truck_snapshot_max_weight_kg=Decimal("100.00"),
        internal_volume_cm3=1_000_000,
        used_volume_cm3=0,
        occupancy_percent=Decimal(0),
        total_weight_kg=Decimal(0),
        loaded_count=0,
        unloaded_count=1,
        algorithm_version="heuristic-v1",
    )


def _rejected_volume(plan_id, order, item, product, org_id=None):
    return LoadPlanItem(
        organization_id=org_id,
        load_plan_id=plan_id,
        order_id=order.id,
        order_item_id=item.id,
        product_id=product.id,
        volume_index=1,
        order_item_snapshot_quantity=1,
        order_item_snapshot_delivery_sequence=1,
        product_snapshot_code=product.code,
        product_snapshot_name=product.name,
        product_snapshot_width_cm=product.width_cm,
        product_snapshot_height_cm=product.height_cm,
        product_snapshot_length_cm=product.length_cm,
        product_snapshot_weight_kg=product.weight_kg,
        product_snapshot_fragile=False,
        product_snapshot_stackable=True,
        product_snapshot_rotation_allowed=True,
        placed=False,
        rejection_reason="NO_VALID_POSITION",
    )


def test_repository_propagates_organization_to_plan_children(session_factory):
    with session_factory() as db:
        other = _other_organization(db)
        truck = _truck(db, other.id, "G05B101")
        order, item, product = _order_and_item(db, other.id)
        plan = _plan(other.id, truck.id)
        plan.orders = [LoadPlanOrder(order_id=order.id)]
        plan.items = [_rejected_volume(None, order, item, product)]

        LoadPlanRepository(db, other.id).add(plan)
        assert plan.organization_id == other.id
        assert plan.orders[0].organization_id == other.id
        assert plan.items[0].organization_id == other.id
        db.flush()


def test_plan_order_link_rejects_other_org_order_even_with_known_uuid(session_factory):
    with session_factory() as db:
        other = _other_organization(db)
        truck_b = _truck(db, other.id, "G05B102")
        order_a, _, _ = _order_and_item(db, LEGACY_ORGANIZATION_ID)
        plan_b = _plan(other.id, truck_b.id)
        db.add(plan_b)
        db.flush()

        with pytest.raises(IntegrityError) as exc, db.begin_nested():
            db.add(
                LoadPlanOrder(
                    organization_id=other.id,
                    load_plan_id=plan_b.id,
                    order_id=order_a.id,
                )
            )
            db.flush()
        assert (
            get_integrity_constraint_name(exc.value)
            == "fk_load_plan_orders__organization_order"
        )


def test_plan_volume_rejects_forged_organization_id(session_factory):
    with session_factory() as db:
        other = _other_organization(db)
        truck_b = _truck(db, other.id, "G05B103")
        order_b, item_b, product_b = _order_and_item(db, other.id)
        plan_b = _plan(other.id, truck_b.id)
        plan_b.orders = [LoadPlanOrder(organization_id=other.id, order_id=order_b.id)]
        db.add(plan_b)
        db.flush()

        volume = _rejected_volume(
            plan_b.id, order_b, item_b, product_b, LEGACY_ORGANIZATION_ID
        )
        with pytest.raises(IntegrityError) as exc, db.begin_nested():
            db.add(volume)
            db.flush()
        assert get_integrity_constraint_name(exc.value) in {
            "fk_load_plan_items__organization_plan_order",
            "fk_load_plan_items__organization_order_item",
            "fk_load_plan_items__organization_product",
        }


def test_repository_rejects_child_with_different_organization(session_factory):
    with session_factory() as db:
        other = _other_organization(db)
        truck_b = _truck(db, other.id, "G05B104")
        order_b, _, _ = _order_and_item(db, other.id)
        plan_b = _plan(other.id, truck_b.id)
        plan_b.orders = [
            LoadPlanOrder(
                organization_id=LEGACY_ORGANIZATION_ID,
                order_id=order_b.id,
            )
        ]

        with pytest.raises(ValueError, match="different organization"):
            LoadPlanRepository(db, other.id).add(plan_b)
