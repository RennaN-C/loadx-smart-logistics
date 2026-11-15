"""G04 PostgreSQL 16 tenant ownership tests for orders and order items."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.pagination import PaginationParams
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.repository import OrderRepository
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID, Organization
from app.modules.products.models import Product


def _organization(db):
    result = Organization(
        legal_name="Transportadora B fictícia",
        display_name="Transportadora B",
        status="PENDING",
    )
    db.add(result)
    db.flush()
    return result


def _customer(db, org_id):
    row = Customer(
        organization_id=org_id,
        name="Cliente fictício",
        document=f"{uuid.uuid4().int % 10**14:014d}",
        address="Rua fictícia",
        city="Curitiba",
        state="PR",
    )
    db.add(row)
    db.flush()
    return row


def _product(db, org_id):
    row = Product(
        organization_id=org_id,
        code=f"SKU-{uuid.uuid4().hex[:10].upper()}",
        name="Produto fictício",
        width_cm=40,
        height_cm=30,
        length_cm=20,
        weight_kg=Decimal("12.50"),
    )
    db.add(row)
    db.flush()
    return row


def _order(db, org_id, customer_id):
    row = Order(
        organization_id=org_id,
        customer_id=customer_id,
        status="DRAFT",
        priority="NORMAL",
        delivery_address="Endereço do teste",
    )
    db.add(row)
    db.flush()
    return row


def test_orders_are_invisible_across_organizations_even_by_known_uuid(
    session_factory,
):
    with session_factory() as db:
        org_b = _organization(db)
        a_customer = _customer(db, LEGACY_ORGANIZATION_ID)
        b_customer = _customer(db, org_b.id)
        a = _order(db, LEGACY_ORGANIZATION_ID, a_customer.id)
        b = _order(db, org_b.id, b_customer.id)

        legacy = OrderRepository(db)
        other = OrderRepository(db, org_b.id)
        assert legacy.get(a.id) is not None
        assert legacy.get(b.id) is None
        assert legacy.get_many([b.id], for_update=True) == []
        assert other.get(a.id) is None
        assert other.get(b.id) is not None
        page = PaginationParams(page=1, page_size=10, sort_order="desc")
        assert [row.id for row in legacy.list(page).items] == [a.id]
        assert [row.id for row in other.list(page).items] == [b.id]


def test_order_cannot_reference_customer_of_another_organization(session_factory):
    with session_factory() as db:
        org_b = _organization(db)
        b_customer = _customer(db, org_b.id)
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                Order(
                    organization_id=LEGACY_ORGANIZATION_ID,
                    customer_id=b_customer.id,
                    status="DRAFT",
                    priority="NORMAL",
                    delivery_address="Tentativa cruzada",
                )
            )
            db.flush()


def test_order_item_cannot_reference_other_org_product_or_order(session_factory):
    with session_factory() as db:
        org_b = _organization(db)
        a_customer = _customer(db, LEGACY_ORGANIZATION_ID)
        b_customer = _customer(db, org_b.id)
        a_order = _order(db, LEGACY_ORGANIZATION_ID, a_customer.id)
        b_order = _order(db, org_b.id, b_customer.id)
        a_product = _product(db, LEGACY_ORGANIZATION_ID)
        b_product = _product(db, org_b.id)

        for order_id, product_id in (
            (a_order.id, b_product.id),
            (b_order.id, a_product.id),
        ):
            with pytest.raises(IntegrityError), db.begin_nested():
                db.add(
                    OrderItem(
                        organization_id=LEGACY_ORGANIZATION_ID,
                        order_id=order_id,
                        product_id=product_id,
                        quantity=1,
                        delivery_sequence=1,
                    )
                )
                db.flush()


def test_order_address_cannot_reference_another_organization(session_factory):
    with session_factory() as db:
        org_b = _organization(db)
        a_customer = _customer(db, LEGACY_ORGANIZATION_ID)
        b_customer = _customer(db, org_b.id)
        address_b = CustomerAddress(
            organization_id=org_b.id,
            customer_id=b_customer.id,
            label="Outra empresa",
            address="Rua do outro tenant",
            city="Curitiba",
            state="PR",
        )
        db.add(address_b)
        db.flush()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                Order(
                    organization_id=LEGACY_ORGANIZATION_ID,
                    customer_id=a_customer.id,
                    customer_address_id=address_b.id,
                    status="DRAFT",
                    priority="NORMAL",
                    delivery_address="Não permitir",
                )
            )
            db.flush()
