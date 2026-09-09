from dataclasses import FrozenInstanceError
from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.rotations import (
    InvalidRotationInputError,
    RotationCode,
    RotationOption,
    generate_rotations,
)


def make_volume(**overrides: object) -> IndividualVolume:
    values: dict[str, object] = {
        "identity": VolumeIdentity(order_item_id=UUID(int=1), volume_index=1),
        "order_id": UUID(int=2),
        "product_id": UUID(int=3),
        "product_name": "Caixa",
        "delivery_sequence": 1,
        "original_width_cm": 10,
        "original_height_cm": 20,
        "original_length_cm": 30,
        "volume_cm3": 6_000,
        "weight_kg": Decimal("10.000"),
        "fragile": False,
        "stackable": True,
        "rotation_allowed": True,
    }
    values.update(overrides)
    return IndividualVolume(**values)  # type: ignore[arg-type]


def test_rotation_codes_follow_the_approved_priority() -> None:
    assert list(RotationCode) == [
        RotationCode.XYZ,
        RotationCode.XZY,
        RotationCode.YXZ,
        RotationCode.YZX,
        RotationCode.ZXY,
        RotationCode.ZYX,
    ]


def test_generate_rotations_returns_all_axis_assignments_in_order() -> None:
    assert generate_rotations(make_volume()) == (
        RotationOption(RotationCode.XYZ, 10, 20, 30),
        RotationOption(RotationCode.XZY, 10, 30, 20),
        RotationOption(RotationCode.YXZ, 20, 10, 30),
        RotationOption(RotationCode.YZX, 20, 30, 10),
        RotationOption(RotationCode.ZXY, 30, 10, 20),
        RotationOption(RotationCode.ZYX, 30, 20, 10),
    )


def test_generate_rotations_keeps_only_original_when_rotation_is_blocked() -> None:
    assert generate_rotations(make_volume(rotation_allowed=False)) == (
        RotationOption(RotationCode.XYZ, 10, 20, 30),
    )


def test_generate_rotations_deduplicates_a_cube() -> None:
    rotations = generate_rotations(
        make_volume(
            original_width_cm=10,
            original_height_cm=10,
            original_length_cm=10,
            volume_cm3=1_000,
        )
    )

    assert rotations == (RotationOption(RotationCode.XYZ, 10, 10, 10),)


def test_generate_rotations_deduplicates_equal_width_and_height_stably() -> None:
    rotations = generate_rotations(
        make_volume(
            original_width_cm=10,
            original_height_cm=10,
            original_length_cm=20,
            volume_cm3=2_000,
        )
    )

    assert rotations == (
        RotationOption(RotationCode.XYZ, 10, 10, 20),
        RotationOption(RotationCode.XZY, 10, 20, 10),
        RotationOption(RotationCode.ZXY, 20, 10, 10),
    )


def test_generate_rotations_deduplicates_equal_width_and_length_stably() -> None:
    rotations = generate_rotations(
        make_volume(
            original_width_cm=10,
            original_height_cm=20,
            original_length_cm=10,
            volume_cm3=2_000,
        )
    )

    assert rotations == (
        RotationOption(RotationCode.XYZ, 10, 20, 10),
        RotationOption(RotationCode.XZY, 10, 10, 20),
        RotationOption(RotationCode.YXZ, 20, 10, 10),
    )


def test_generate_rotations_deduplicates_equal_height_and_length_stably() -> None:
    rotations = generate_rotations(
        make_volume(
            original_width_cm=20,
            original_height_cm=10,
            original_length_cm=10,
            volume_cm3=2_000,
        )
    )

    assert rotations == (
        RotationOption(RotationCode.XYZ, 20, 10, 10),
        RotationOption(RotationCode.YXZ, 10, 20, 10),
        RotationOption(RotationCode.YZX, 10, 10, 20),
    )


def test_generate_rotations_preserves_the_physical_volume() -> None:
    volume = make_volume()

    for rotation in generate_rotations(volume):
        assert (
            rotation.used_width_cm * rotation.used_height_cm * rotation.used_length_cm
            == volume.volume_cm3
        )


def test_generate_rotations_is_deterministic_and_does_not_mutate_volume() -> None:
    volume = make_volume()

    first_result = generate_rotations(volume)
    second_result = generate_rotations(volume)

    assert first_result == second_result
    assert volume == make_volume()


def test_rotation_option_is_immutable() -> None:
    rotation = generate_rotations(make_volume())[0]

    with pytest.raises(FrozenInstanceError):
        rotation.used_width_cm = 99


def test_generate_rotations_rejects_invalid_volume_contract() -> None:
    with pytest.raises(InvalidRotationInputError) as exc_info:
        generate_rotations(object())  # type: ignore[arg-type]

    assert exc_info.value.code == "INVALID_ROTATION_INPUT"
    assert exc_info.value.field_name == "volume"


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("original_width_cm", 0),
        ("original_height_cm", -1),
        ("original_length_cm", True),
        ("original_width_cm", 1.5),
        ("original_height_cm", "20"),
    ],
)
def test_generate_rotations_rejects_invalid_dimensions(
    field_name: str,
    invalid_value: object,
) -> None:
    with pytest.raises(InvalidRotationInputError) as exc_info:
        generate_rotations(make_volume(**{field_name: invalid_value}))

    assert exc_info.value.field_name == field_name


def test_generate_rotations_requires_boolean_permission() -> None:
    with pytest.raises(InvalidRotationInputError) as exc_info:
        generate_rotations(make_volume(rotation_allowed=1))

    assert exc_info.value.field_name == "rotation_allowed"
