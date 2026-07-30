from app.database.base import Base


def test_base_metadata_uses_project_naming_convention() -> None:
    convention = Base.metadata.naming_convention

    assert convention["pk"] == "pk_%(table_name)s"
    assert convention["fk"] == "fk_%(table_name)s__%(referred_table_name)s"
    assert convention["ix"] == "ix_%(table_name)s__%(column_0_N_name)s"
    assert convention["uq"] == "uq_%(table_name)s__%(column_0_N_name)s"
    assert convention["ck"] == "ck_%(table_name)s__%(constraint_name)s"
