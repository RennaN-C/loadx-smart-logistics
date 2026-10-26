from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index

from app.database.base import Base
from app.modules.status_history.models import AuditEvent, StatusHistory
from app.modules.users.models import User


def test_status_history_model_is_registered_in_metadata() -> None:
    assert User.__table__ is Base.metadata.tables["users"]
    assert StatusHistory.__table__ is Base.metadata.tables["status_history"]


def test_status_history_table_uses_uuid_primary_key() -> None:
    table = Base.metadata.tables["status_history"]

    assert table.primary_key.name == "pk_status_history"
    assert [column.name for column in table.primary_key.columns] == ["id"]


def test_status_history_foreign_key_follows_documented_name() -> None:
    table = Base.metadata.tables["status_history"]
    actual_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert "fk_status_history__users" in actual_names


def test_status_history_indexes_follow_documented_names() -> None:
    table = Base.metadata.tables["status_history"]
    actual_indexes = {
        index.name: [column.name for column in index.columns]
        for index in table.indexes
        if isinstance(index, Index)
    }

    assert actual_indexes["ix_status_history__entity"] == ["entity_type", "entity_id"]
    assert actual_indexes["ix_status_history__created_at"] == ["created_at"]


def test_status_history_entity_type_uses_closed_catalog() -> None:
    table = Base.metadata.tables["status_history"]
    actual_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_status_history__entity_type_allowed" in actual_names


def test_audit_event_model_is_registered_in_metadata() -> None:
    assert AuditEvent.__table__ is Base.metadata.tables["audit_events"]


def test_audit_event_constraints_and_indexes_follow_contract() -> None:
    table = Base.metadata.tables["audit_events"]
    constraint_names = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert "pk_audit_events" in constraint_names
    assert "fk_audit_events__users" in constraint_names
    assert "ck_audit_events__event_type_allowed" in constraint_names
    assert "ck_audit_events__entity_type_allowed" in constraint_names
    assert "ix_audit_events__entity" in index_names
    assert "ix_audit_events__actor_id" in index_names
    assert "ix_audit_events__created_at" in index_names
