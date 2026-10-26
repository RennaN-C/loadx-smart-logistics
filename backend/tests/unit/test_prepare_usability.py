import pytest

from scripts.prepare_usability import batch_number, demo_plate


@pytest.mark.parametrize("batch", ["", "../gravacao", "Gravacao", "a", "x" * 25])
def test_recording_batch_rejects_ambiguous_or_path_like_names(batch):
    with pytest.raises(ValueError, match="Lote"):
        batch_number(batch)


def test_rehearsal_and_recording_have_stable_distinct_vehicle_identifiers():
    rehearsal = batch_number("ensaio-01")
    recording = batch_number("gravacao-01")
    assert rehearsal == batch_number("ensaio-01")
    assert rehearsal != recording
    plates = [
        demo_plate(number + index)
        for number in (rehearsal, recording)
        for index in range(3)
    ]
    assert len(set(plates)) == 6
    assert all(len(plate) == 7 and plate[:2] == "VD" for plate in plates)
