from sqlalchemy import CheckConstraint, UniqueConstraint

from app.database.base import Base
from app.modules.customers.models import Customer
from app.modules.drivers.models import Driver
from app.modules.products.models import Product
from app.modules.trucks.models import Truck
from app.modules.users.models import User


def test_core_catalog_models_are_registered_in_metadata() -> None:
    assert User.__table__ is Base.metadata.tables["users"]
    assert Customer.__table__ is Base.metadata.tables["customers"]
    assert Driver.__table__ is Base.metadata.tables["drivers"]
    assert Truck.__table__ is Base.metadata.tables["trucks"]
    assert Product.__table__ is Base.metadata.tables["products"]


def test_core_catalog_tables_use_uuid_primary_key() -> None:
    for table_name in ("users", "customers", "drivers", "trucks", "products"):
        table = Base.metadata.tables[table_name]
        assert table.primary_key.name == f"pk_{table_name}"
        assert [column.name for column in table.primary_key.columns] == ["id"]


def test_core_catalog_unique_constraints_follow_documented_names() -> None:
    expected_unique_constraints = {
        "users": {"uq_users__email"},
        "customers": {"uq_customers__document"},
        "drivers": {"uq_drivers__document", "uq_drivers__license_number"},
        "trucks": {"uq_trucks__plate"},
        "products": {"uq_products__code"},
    }

    for table_name, expected_names in expected_unique_constraints.items():
        table = Base.metadata.tables[table_name]
        actual_names = {constraint.name for constraint in table.constraints if isinstance(constraint, UniqueConstraint)}
        assert expected_names <= actual_names


def test_physical_constraints_are_registered_for_capacity_rules() -> None:
    expected_check_constraints = {
        "users": {"ck_users__role_allowed"},
        "trucks": {"ck_trucks__dimensions_positive", "ck_trucks__max_weight_positive"},
        "products": {"ck_products__dimensions_positive", "ck_products__weight_positive"},
    }

    for table_name, expected_names in expected_check_constraints.items():
        table = Base.metadata.tables[table_name]
        actual_names = {constraint.name for constraint in table.constraints if isinstance(constraint, CheckConstraint)}
        assert expected_names <= actual_names
