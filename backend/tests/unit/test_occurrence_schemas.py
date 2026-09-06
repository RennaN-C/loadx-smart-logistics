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


def test_occurrence_schema_accepts_controlled_mock_photo_reference() -> None:
    occurrence = OccurrenceCreate(
        trip_id="49f84d96-7c3b-418b-92df-7a8e5fa16c21",
        type="DAMAGED_PRODUCT",
        description="Avaria controlada.",
        photo_url="mock://occurrences/photo-1",
    )

    assert occurrence.photo_url == "mock://occurrences/photo-1"


def test_occurrence_schema_keeps_photo_optional() -> None:
    occurrence = OccurrenceCreate(
        trip_id="49f84d96-7c3b-418b-92df-7a8e5fa16c21",
        type="DELAY",
        description="Atraso operacional.",
    )

    assert occurrence.photo_url is None


@pytest.mark.parametrize(
    "photo_url",
    [
        "",
        "   ",
        "https://example.test/photo-1",
        "mock://occurrences/",
        "mock://other/photo-1",
        "mock://occurrences/photo 1",
        "mock://occurrences/photo-1?token=example",
        "mock://occurrences/photo-1#fragment",
    ],
)
def test_occurrence_schema_rejects_uncontrolled_photo_reference(
    photo_url: str,
) -> None:
    with pytest.raises(ValidationError):
        OccurrenceCreate(
            trip_id="49f84d96-7c3b-418b-92df-7a8e5fa16c21",
            type="DAMAGED_PRODUCT",
            description="Avaria controlada.",
            photo_url=photo_url,
        )
