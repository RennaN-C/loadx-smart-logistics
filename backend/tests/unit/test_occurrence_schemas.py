import pytest
from pydantic import ValidationError

from app.modules.occurrences.schemas import OccurrenceCreate


def test_occurrence_schema_normalizes_supported_type() -> None:
    occurrence = OccurrenceCreate(
        trip_id="49f84d96-7c3b-418b-92df-7a8e5fa16c21",
        type="delay",
        description="Atraso operacional.",
    )

    assert occurrence.type == "DELAY"


def test_occurrence_schema_rejects_unsupported_type() -> None:
    with pytest.raises(ValidationError):
        OccurrenceCreate(
            trip_id="49f84d96-7c3b-418b-92df-7a8e5fa16c21",
            type="UNSUPPORTED",
            description="Tipo inválido.",
        )
