from dataclasses import FrozenInstanceError
from decimal import Decimal
from itertools import permutations
from uuid import UUID

import pytest

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.geometry import (
    InternalDimensions,
    PositionedAABB,
)
from app.modules.load_planning.optimizer.loading_sequence import (
    InvalidLoadingSequenceInputError,
    assign_loading_sequences,
    calculate_door_distance_cm,
    is_candidate_delivery_depth_valid,
    is_delivery_depth_configuration_valid,
)
from app.modules.load_planning.optimizer.placement import PlacementCandidate
from app.modules.load_planning.optimizer.rotations import (
    RotationCode,
    RotationOption,
)


def make_placement(
    identity_number: int,
    *,
    volume_index: int = 1,
    delivery_sequence: int = 1,
    position_x_cm: int = 0,
    position_y_cm: int = 0,
    position_z_cm: int = 0,
    used_width_cm: int = 10,
    used_height_cm: int = 10,
    used_length_cm: int = 10,
    fragile: bool = False,
    stackable: bool = True,
) -> PlacementCandidate:
    identity = VolumeIdentity(UUID(int=identity_number), volume_index)
    volume = IndividualVolume(
        identity=identity,
        order_id=UUID(int=100 + identity_number),
        product_id=UUID(int=200 + identity_number),
        product_name=f"Volume {identity_number}",
        delivery_sequence=delivery_sequence,
        original_width_cm=used_width_cm,
        original_height_cm=used_height_cm,
        original_length_cm=used_length_cm,
        volume_cm3=used_width_cm * used_height_cm * used_length_cm,
        weight_kg=Decimal("1.000"),
        fragile=fragile,
        stackable=stackable,
        rotation_allowed=False,
    )
    rotation = RotationOption(
        RotationCode.XYZ,
        used_width_cm,
        used_height_cm,
        used_length_cm,
    )
    return PlacementCandidate(
        volume=volume,
        rotation=rotation,
        box=PositionedAABB(
            position_x_cm,
            position_y_cm,
            position_z_cm,
            used_width_cm,
            used_height_cm,
            used_length_cm,
        ),
    )


def test_door_distance_uses_the_face_toward_z_internal_length() -> None:
    placement = make_placement(1, position_z_cm=60, used_length_cm=30)

    assert (
        calculate_door_distance_cm(
            placement,
            InternalDimensions(20, 20, 100),
        )
        == 10
    )


def test_later_delivery_must_be_at_least_as_deep_as_earlier_delivery() -> None:
    bounds = InternalDimensions(20, 20, 100)
    earlier = make_placement(1, delivery_sequence=1, position_z_cm=80)
    later_deeper = make_placement(
        2,
        delivery_sequence=2,
        position_x_cm=10,
        position_z_cm=60,
    )
    later_shallower = make_placement(
        3,
        delivery_sequence=2,
        position_x_cm=10,
        position_z_cm=90,
    )

    assert is_delivery_depth_configuration_valid([earlier, later_deeper], bounds)
    assert not is_delivery_depth_configuration_valid([earlier, later_shallower], bounds)


def test_equal_depth_is_allowed_for_different_deliveries() -> None:
    bounds = InternalDimensions(20, 20, 100)
    first = make_placement(1, delivery_sequence=1, position_z_cm=60)
    second = make_placement(
        2,
        delivery_sequence=2,
        position_x_cm=10,
        position_z_cm=60,
    )

    assert is_delivery_depth_configuration_valid([first, second], bounds)


def test_equal_delivery_does_not_impose_a_depth_relation() -> None:
    bounds = InternalDimensions(20, 20, 100)
    deep = make_placement(1, delivery_sequence=2, position_z_cm=0)
    shallow = make_placement(
        2,
        delivery_sequence=2,
        position_x_cm=10,
        position_z_cm=90,
    )

    assert is_delivery_depth_configuration_valid([deep, shallow], bounds)


def test_candidate_depth_validation_checks_the_whole_tentative_layout() -> None:
    bounds = InternalDimensions(20, 20, 100)
    earlier = make_placement(1, delivery_sequence=1, position_z_cm=60)
    invalid_later = make_placement(
        2,
        delivery_sequence=2,
        position_x_cm=10,
        position_z_cm=80,
    )

    assert not is_candidate_delivery_depth_valid(
        invalid_later,
        [earlier],
        bounds,
    )


def test_loading_sequence_uses_kahn_priority_only_among_ready_volumes() -> None:
    bounds = InternalDimensions(30, 20, 20)
    support = make_placement(10, delivery_sequence=1)
    top = make_placement(1, delivery_sequence=99, position_y_cm=10)
    unrelated = make_placement(
        2,
        delivery_sequence=2,
        position_x_cm=20,
    )

    result = assign_loading_sequences([top, support, unrelated], bounds)

    assert [item.identity for item in result] == [
        unrelated.identity,
        support.identity,
        top.identity,
    ]
    assert [item.loading_sequence for item in result] == [1, 2, 3]


def test_every_direct_support_precedes_a_volume_with_multiple_supports() -> None:
    bounds = InternalDimensions(10, 20, 10)
    left = make_placement(2, used_width_cm=5)
    right = make_placement(1, position_x_cm=5, used_width_cm=5)
    top = make_placement(3, delivery_sequence=9, position_y_cm=10)

    result = assign_loading_sequences([top, left, right], bounds)

    assert [item.identity for item in result] == [
        right.identity,
        left.identity,
        top.identity,
    ]


def test_ready_volumes_use_delivery_then_distance_then_identity() -> None:
    bounds = InternalDimensions(40, 10, 100)
    earlier = make_placement(
        4,
        delivery_sequence=1,
        position_x_cm=30,
        position_z_cm=90,
    )
    later_shallow = make_placement(
        3,
        delivery_sequence=2,
        position_x_cm=20,
        position_z_cm=70,
    )
    later_deep_high_identity = make_placement(
        2,
        delivery_sequence=2,
        position_x_cm=10,
        position_z_cm=50,
    )
    later_deep_low_identity = make_placement(
        1,
        delivery_sequence=2,
        position_z_cm=50,
    )

    result = assign_loading_sequences(
        [earlier, later_shallow, later_deep_high_identity, later_deep_low_identity],
        bounds,
    )

    assert [item.identity for item in result] == [
        later_deep_low_identity.identity,
        later_deep_high_identity.identity,
        later_shallow.identity,
        earlier.identity,
    ]


def test_loading_sequence_uses_volume_index_as_the_last_tie_break() -> None:
    bounds = InternalDimensions(20, 10, 10)
    second = make_placement(1, volume_index=2, position_x_cm=10)
    first = make_placement(1, volume_index=1)

    result = assign_loading_sequences([second, first], bounds)

    assert [item.identity for item in result] == [first.identity, second.identity]


def test_loading_sequence_is_independent_of_input_order() -> None:
    bounds = InternalDimensions(30, 20, 20)
    placements = (
        make_placement(1),
        make_placement(2, position_x_cm=10),
        make_placement(3, position_x_cm=20),
    )
    expected = assign_loading_sequences(placements, bounds)

    for candidate_order in permutations(placements):
        assert assign_loading_sequences(candidate_order, bounds) == expected


def test_loading_sequence_rejects_invalid_support_configuration() -> None:
    floating = make_placement(1, position_y_cm=10)

    with pytest.raises(InvalidLoadingSequenceInputError) as exc_info:
        assign_loading_sequences(
            [floating],
            InternalDimensions(10, 20, 10),
        )

    assert exc_info.value.field_name == "placements"
    assert "support" in exc_info.value.reason


def test_loading_sequence_rejects_non_monotonic_delivery_depth() -> None:
    bounds = InternalDimensions(20, 10, 100)
    earlier_deep = make_placement(1, delivery_sequence=1, position_z_cm=20)
    later_shallow = make_placement(
        2,
        delivery_sequence=2,
        position_x_cm=10,
        position_z_cm=80,
    )

    with pytest.raises(InvalidLoadingSequenceInputError) as exc_info:
        assign_loading_sequences([earlier_deep, later_shallow], bounds)

    assert "depth" in exc_info.value.reason


def test_loading_sequence_rejects_unordered_and_duplicate_inputs() -> None:
    placement = make_placement(1)
    bounds = InternalDimensions(20, 10, 10)

    with pytest.raises(InvalidLoadingSequenceInputError):
        assign_loading_sequences({placement}, bounds)  # type: ignore[arg-type]
    with pytest.raises(InvalidLoadingSequenceInputError) as duplicate_error:
        assign_loading_sequences([placement, placement], bounds)

    assert duplicate_error.value.field_name == "placements"


def test_sequenced_placement_is_immutable() -> None:
    result = assign_loading_sequences(
        [make_placement(1)],
        InternalDimensions(10, 10, 10),
    )[0]

    with pytest.raises(FrozenInstanceError):
        result.loading_sequence = 2  # type: ignore[misc]


def test_empty_configuration_has_an_empty_loading_sequence() -> None:
    assert assign_loading_sequences([], InternalDimensions(10, 10, 10)) == ()
