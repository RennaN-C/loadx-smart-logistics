from sqlalchemy import CheckConstraint, ForeignKeyConstraint

from app.database.base import Base
from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem
from app.modules.products.models import Product


def test_order_models_are_registered_in_metadata() -> None:
    assert Customer.__table__ is Base.metadata.tables["customers"]
    assert Product.__table__ is Base.metadata.tables["products"]
    assert Order.__table__ is Base.metadata.tables["orders"]
    assert OrderItem.__table__ is Base.metadata.tables["order_items"]


def test_order_tables_use_uuid_primary_key() -> None:
    for table_name in ("orders", "order_items"):
        table = Base.metadata.tables[table_name]
        assert table.primary_key.name == f"pk_{table_name}"
        assert [column.name for column in table.primary_key.columns] == ["id"]


def test_order_foreign_keys_follow_documented_names() -> None:
    expected_foreign_keys = {
        "orders": {"fk_orders__customers"},
        "order_items": {"fk_order_items__orders", "fk_order_items__products"},
    }

    for table_name, expected_names in expected_foreign_keys.items():
        table = Base.metadata.tables[table_name]
        actual_names = {constraint.name for constraint in table.constraints if isinstance(constraint, ForeignKeyConstraint)}
        assert expected_names <= actual_names


def test_order_check_constraints_follow_documented_names() -> None:
    expected_check_constraints = {
        "orders": {"ck_orders__status_allowed"},
        "order_items": {"ck_order_items__quantity_positive", "ck_order_items__delivery_sequence_positive"},
    }

    for table_name, expected_names in expected_check_constraints.items():
        table = Base.metadata.tables[table_name]
        actual_names = {constraint.name for constraint in table.constraints if isinstance(constraint, CheckConstraint)}
        assert expected_names <= actual_names
