from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, UniqueConstraint

from app.database.base import Base
from app.modules.deliveries.models import Delivery, Trip


def constraint_names(table, constraint_type: type) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type) and constraint.name is not None
    }


def test_trip_and_delivery_tables_are_registered() -> None:
    assert Trip.__table__ is Base.metadata.tables["trips"]
    assert Delivery.__table__ is Base.metadata.tables["deliveries"]


def test_trip_constraints_protect_status_timestamps_and_load_plan() -> None:
    assert {
        "ck_trips__status_allowed",
        "ck_trips__timestamps_consistent",
    } <= constraint_names(Trip.__table__, CheckConstraint)
    assert "uq_trips__load_plan_id" in constraint_names(
        Trip.__table__, UniqueConstraint
    )


def test_trip_created_at_is_required_timezone_aware_and_server_generated() -> None:
    created_at = Trip.__table__.c.created_at

    assert isinstance(created_at.type, DateTime)
    assert created_at.type.timezone is True
    assert created_at.nullable is False
    assert created_at.server_default is not None


def test_delivery_constraints_protect_order_sequence_and_completion() -> None:
    assert {
        "ck_deliveries__status_allowed",
        "ck_deliveries__sequence_positive",
        "ck_deliveries__completion_consistent",
    } <= constraint_names(Delivery.__table__, CheckConstraint)
    assert {
        "uq_deliveries__order_id",
        "uq_deliveries__trip_order",
        "uq_deliveries__trip_sequence",
    } <= constraint_names(Delivery.__table__, UniqueConstraint)


def test_operational_foreign_keys_are_restrictive() -> None:
    foreign_keys = [
        constraint
        for table in (Trip.__table__, Delivery.__table__)
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert {constraint.name for constraint in foreign_keys} == {
        "fk_trips__drivers",
        "fk_trips__load_plans",
        "fk_deliveries__orders",
        "fk_deliveries__trips",
    }
    assert all(constraint.ondelete == "RESTRICT" for constraint in foreign_keys)
