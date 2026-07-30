from sqlalchemy import ForeignKeyConstraint, Index

from app.database.base import Base
from app.modules.status_history.models import StatusHistory
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
    actual_names = {constraint.name for constraint in table.constraints if isinstance(constraint, ForeignKeyConstraint)}

    assert "fk_status_history__users" in actual_names


def test_status_history_indexes_follow_documented_names() -> None:
    table = Base.metadata.tables["status_history"]
    actual_indexes = {index.name: [column.name for column in index.columns] for index in table.indexes if isinstance(index, Index)}

    assert actual_indexes["ix_status_history__entity"] == ["entity_type", "entity_id"]
    assert actual_indexes["ix_status_history__created_at"] == ["created_at"]
