"""G02: scope product and customer registries using two synthetic organizations."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.customers.address_repository import CustomerAddressRepository
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.customers.repository import CustomerRepository
from app.modules.organizations.models import LEGACY_ORGANIZATION_ID, Organization
from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository


def other_organization(db):
    org = Organization(legal_name="Empresa B fictícia", display_name="Empresa B")
    db.add(org)
    db.flush()
    return org


def customer(db, org_id):
    row = Customer(
        organization_id=org_id,
        name="Cliente fictício",
        document="00000000000001",
        address="Rua de teste",
        city="Curitiba",
        state="PR",
    )
    db.add(row)
    db.flush()
    return row


def product(db, org_id):
    row = Product(
        organization_id=org_id,
        code="SKU-TESTE-01",
        name="Produto fictício",
        width_cm=10,
        height_cm=20,
        length_cm=30,
        weight_kg=Decimal("1.500"),
    )
    db.add(row)
    db.flush()
    return row


def test_same_customer_document_can_exist_in_two_organizations(session_factory):
    with session_factory() as db:
        other = other_organization(db)
        a = customer(db, LEGACY_ORGANIZATION_ID)
        b = customer(db, other.id)
        assert a.document == b.document
        assert CustomerRepository(db).get(b.id) is None
        assert CustomerRepository(db).get_by_document(a.document).id == a.id
        assert CustomerRepository(db, other.id).get(a.id) is None
        assert CustomerRepository(db, other.id).get_by_document(a.document).id == b.id


def test_product_uuid_and_codes_are_tenant_scoped(session_factory):
    with session_factory() as db:
        other = other_organization(db)
        a = product(db, LEGACY_ORGANIZATION_ID)
        b = product(db, other.id)
        repository = ProductRepository(db)
        assert a.code == b.code
        assert repository.get(b.id) is None
        assert repository.get_many([b.id]) == []
        assert repository.get_by_code(a.code).id == a.id
        assert ProductRepository(db, other.id).get(a.id) is None
        assert ProductRepository(db, other.id).get_by_code(b.code).id == b.id


def test_customer_address_composite_fk_rejects_cross_org_parent(session_factory):
    with session_factory() as db:
        other = other_organization(db)
        b = customer(db, other.id)
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(
                CustomerAddress(
                    organization_id=LEGACY_ORGANIZATION_ID,
                    customer_id=b.id,
                    label="Outro tenant",
                    address="Rua inexistente",
                    city="Florianópolis",
                    state="SC",
                )
            )
            db.flush()


def test_address_repository_does_not_reveal_other_org_uuid(session_factory):
    with session_factory() as db:
        other = other_organization(db)
        b = customer(db, other.id)
        address = CustomerAddress(
            organization_id=other.id,
            customer_id=b.id,
            label="Filial",
            address="Rua de teste",
            city="Florianópolis",
            state="SC",
        )
        db.add(address)
        db.flush()
        assert CustomerAddressRepository(db).get_for_update(b.id, address.id) is None
        assert (
            CustomerAddressRepository(db, other.id).get_for_update(b.id, address.id)
            is not None
        )
