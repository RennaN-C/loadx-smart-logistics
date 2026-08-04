from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.geometry import (
    InternalDimensions,
    PositionedAABB,
    is_collision_free,
)
from app.modules.load_planning.optimizer.placement import (
    PlacementCandidate,
    select_first_valid_candidate,
)
from app.modules.load_planning.optimizer.rotations import (
    RotationCode,
    RotationOption,
)
from app.modules.load_planning.optimizer.support import (
    InvalidSupportInputError,
    SupportAssessment,
    analyze_support_configuration,
    is_candidate_support_valid,
    is_support_configuration_valid,
)


def make_candidate(
    identity_number: int,
    *,
    position_x_cm: int = 0,
    position_y_cm: int = 0,
    position_z_cm: int = 0,
    used_width_cm: int = 10,
    used_height_cm: int = 10,
    used_length_cm: int = 10,
    weight_kg: object = Decimal("1.000"),
    fragile: object = False,
    stackable: object = True,
) -> PlacementCandidate:
    identity = VolumeIdentity(
        order_item_id=UUID(int=identity_number),
        volume_index=1,
    )
    volume = IndividualVolume(
        identity=identity,
        order_id=UUID(int=100 + identity_number),
        product_id=UUID(int=200 + identity_number),
        product_name=f"Volume {identity_number}",
        delivery_sequence=1,
        original_width_cm=used_width_cm,
        original_height_cm=used_height_cm,
        original_length_cm=used_length_cm,
        volume_cm3=used_width_cm * used_height_cm * used_length_cm,
        weight_kg=weight_kg,  # type: ignore[arg-type]
        fragile=fragile,  # type: ignore[arg-type]
        stackable=stackable,  # type: ignore[arg-type]
        rotation_allowed=False,
    )
    rotation = RotationOption(
        rotation_code=RotationCode.XYZ,
        used_width_cm=used_width_cm,
        used_height_cm=used_height_cm,
        used_length_cm=used_length_cm,
    )
    return PlacementCandidate(
        volume=volume,
        rotation=rotation,
        box=PositionedAABB(
            position_x_cm=position_x_cm,
            position_y_cm=position_y_cm,
            position_z_cm=position_z_cm,
            used_width_cm=used_width_cm,
            used_height_cm=used_height_cm,
            used_length_cm=used_length_cm,
        ),
    )


def assessment_for(
    candidate: PlacementCandidate,
    placements: list[PlacementCandidate],
) -> SupportAssessment:
    return next(
        assessment
        for assessment in analyze_support_configuration(placements)
        if assessment.identity == candidate.identity
    )


def test_empty_support_configuration_is_valid() -> None:
    assert analyze_support_configuration([]) == ()
    assert is_support_configuration_valid([])


def test_candidate_on_floor_is_fully_supported_without_supporters() -> None:
    candidate = make_candidate(1, fragile=True, stackable=False)

    assessment = assessment_for(candidate, [candidate])

    assert assessment.on_floor
    assert assessment.base_area_cm2 == 100
    assert assessment.supported_area_cm2 == 100
    assert assessment.direct_supporter_identities == ()
    assert assessment.load_bearing_supporter_identities == ()
    assert assessment.is_fully_supported
    assert is_candidate_support_valid(candidate, [])


def test_single_support_can_cover_the_base_exactly() -> None:
    support = make_candidate(1)
    candidate = make_candidate(2, position_y_cm=10)

    assessment = assessment_for(candidate, [support, candidate])

    assert assessment.supported_area_cm2 == assessment.base_area_cm2 == 100
    assert assessment.direct_supporter_identities == (support.identity,)
    assert is_candidate_support_valid(candidate, [support])


def test_support_larger_than_candidate_is_clipped_to_the_base() -> None:
    support = make_candidate(1, used_width_cm=20, used_length_cm=20)
    candidate = make_candidate(
        2,
        position_x_cm=5,
        position_y_cm=10,
        position_z_cm=5,
    )

    assessment = assessment_for(candidate, [support, candidate])

    assert assessment.supported_area_cm2 == assessment.base_area_cm2 == 100
    assert is_candidate_support_valid(candidate, [support])


def test_candidate_without_support_above_floor_is_invalid() -> None:
    candidate = make_candidate(1, position_y_cm=10)

    assert not is_candidate_support_valid(candidate, [])


def test_partial_support_and_overhang_are_invalid() -> None:
    support = make_candidate(1)
    candidate = make_candidate(2, position_x_cm=5, position_y_cm=10)

    assessment = assessment_for(candidate, [support, candidate])

    assert assessment.supported_area_cm2 == 50
    assert not assessment.is_fully_supported
    assert not is_candidate_support_valid(candidate, [support])


def test_two_adjacent_supports_cover_the_full_base() -> None:
    left = make_candidate(1, used_width_cm=5)
    right = make_candidate(2, position_x_cm=5, used_width_cm=5)
    candidate = make_candidate(3, position_y_cm=10)

    assessment = assessment_for(candidate, [left, right, candidate])

    assert assessment.supported_area_cm2 == 100
    assert assessment.direct_supporter_identities == (
        left.identity,
        right.identity,
    )
    assert is_candidate_support_valid(candidate, [left, right])


def test_four_supports_can_cover_the_base_as_a_mosaic() -> None:
    supports = [
        make_candidate(1, used_width_cm=5, used_length_cm=5),
        make_candidate(
            2,
            position_x_cm=5,
            used_width_cm=5,
            used_length_cm=5,
        ),
        make_candidate(
            3,
            position_z_cm=5,
            used_width_cm=5,
            used_length_cm=5,
        ),
        make_candidate(
            4,
            position_x_cm=5,
            position_z_cm=5,
            used_width_cm=5,
            used_length_cm=5,
        ),
    ]
    candidate = make_candidate(5, position_y_cm=10)

    assert is_candidate_support_valid(candidate, supports)


def test_overlapping_support_areas_are_not_counted_twice() -> None:
    first = make_candidate(1, used_width_cm=6)
    second = make_candidate(2, used_width_cm=6)
    candidate = make_candidate(3, position_y_cm=10)

    assessment = assessment_for(candidate, [first, second, candidate])

    assert assessment.supported_area_cm2 == 60
    assert not is_candidate_support_valid(candidate, [first, second])


def test_overlapping_area_does_not_hide_a_one_centimeter_gap() -> None:
    left = make_candidate(1, used_width_cm=6)
    right = make_candidate(2, position_x_cm=5, used_width_cm=4)
    candidate = make_candidate(3, position_y_cm=10)

    assessment = assessment_for(candidate, [left, right, candidate])

    assert assessment.supported_area_cm2 == 90
    assert not is_candidate_support_valid(candidate, [left, right])


def test_support_outside_the_footprint_does_not_compensate_a_gap() -> None:
    partial = make_candidate(1, used_width_cm=5)
    outside = make_candidate(2, position_x_cm=10, used_width_cm=10)
    candidate = make_candidate(3, position_y_cm=10)

    assessment = assessment_for(candidate, [partial, outside, candidate])

    assert assessment.supported_area_cm2 == 50
    assert not is_candidate_support_valid(candidate, [partial, outside])


@pytest.mark.parametrize(
    "support",
    [
        make_candidate(1, position_x_cm=10),
        make_candidate(1, position_x_cm=10, position_z_cm=10),
    ],
)
def test_edge_and_vertex_contact_do_not_provide_support(
    support: PlacementCandidate,
) -> None:
    candidate = make_candidate(2, position_y_cm=10)

    assert assessment_for(candidate, [support, candidate]).supported_area_cm2 == 0
    assert not is_candidate_support_valid(candidate, [support])


@pytest.mark.parametrize("support_height_cm", [9, 11])
def test_support_top_must_equal_candidate_bottom_exactly(
    support_height_cm: int,
) -> None:
    support = make_candidate(1, used_height_cm=support_height_cm)
    candidate = make_candidate(2, position_y_cm=10)

    assert assessment_for(candidate, [support, candidate]).supported_area_cm2 == 0
    assert not is_candidate_support_valid(candidate, [support])


def test_non_stackable_direct_support_invalidates_configuration() -> None:
    support = make_candidate(1, stackable=False)
    candidate = make_candidate(2, position_y_cm=10)

    assert not is_candidate_support_valid(candidate, [support])


def test_non_stackable_candidate_can_be_placed_on_top() -> None:
    support = make_candidate(1)
    candidate = make_candidate(2, position_y_cm=10, stackable=False)

    assert is_candidate_support_valid(candidate, [support])


def test_non_stackable_box_without_positive_contact_is_irrelevant() -> None:
    safe_support = make_candidate(1)
    edge_contact = make_candidate(2, position_x_cm=10, stackable=False)
    candidate = make_candidate(3, position_y_cm=10)

    assert is_candidate_support_valid(candidate, [safe_support, edge_contact])


def test_redundant_non_stackable_support_with_positive_contact_is_invalid() -> None:
    safe_support = make_candidate(1)
    unsafe_support = make_candidate(2, stackable=False)
    candidate = make_candidate(3, position_y_cm=10)

    assert not is_candidate_support_valid(
        candidate,
        [safe_support, unsafe_support],
    )


def test_fragile_direct_support_rejects_any_positive_weight() -> None:
    support = make_candidate(1, fragile=True)
    candidate = make_candidate(
        2,
        position_y_cm=10,
        weight_kg=Decimal("0.001"),
    )

    assert not is_candidate_support_valid(candidate, [support])


def test_fragile_candidate_can_be_placed_on_safe_support() -> None:
    support = make_candidate(1)
    candidate = make_candidate(2, position_y_cm=10, fragile=True)

    assert is_candidate_support_valid(candidate, [support])


def test_fragile_box_without_positive_contact_is_irrelevant() -> None:
    safe_support = make_candidate(1)
    edge_contact = make_candidate(2, position_x_cm=10, fragile=True)
    candidate = make_candidate(3, position_y_cm=10)

    assert is_candidate_support_valid(candidate, [safe_support, edge_contact])


def test_redundant_fragile_support_with_positive_contact_is_invalid() -> None:
    safe_support = make_candidate(1)
    fragile_support = make_candidate(2, fragile=True)
    candidate = make_candidate(3, position_y_cm=10)

    assert not is_candidate_support_valid(
        candidate,
        [safe_support, fragile_support],
    )


def test_assessment_exposes_direct_and_transmitted_load_bearers() -> None:
    bottom = make_candidate(1)
    middle = make_candidate(2, position_y_cm=10)
    top = make_candidate(3, position_y_cm=20)

    assessment = assessment_for(top, [bottom, middle, top])

    assert assessment.direct_supporter_identities == (middle.identity,)
    assert assessment.load_bearing_supporter_identities == (
        bottom.identity,
        middle.identity,
    )
    assert is_support_configuration_valid([bottom, middle, top])


def test_fragile_ancestor_rejects_transmitted_load() -> None:
    bottom = make_candidate(1, fragile=True)
    middle = make_candidate(2, position_y_cm=10)
    top = make_candidate(3, position_y_cm=20)

    assessment = assessment_for(top, [bottom, middle, top])

    assert bottom.identity not in assessment.direct_supporter_identities
    assert bottom.identity in assessment.load_bearing_supporter_identities
    assert not is_candidate_support_valid(top, [bottom, middle])


def test_common_ancestor_is_deduplicated_across_multiple_support_paths() -> None:
    bottom = make_candidate(1)
    left = make_candidate(2, position_y_cm=10, used_width_cm=5)
    right = make_candidate(
        3,
        position_x_cm=5,
        position_y_cm=10,
        used_width_cm=5,
    )
    top = make_candidate(4, position_y_cm=20)

    assessment = assessment_for(top, [bottom, left, right, top])

    assert assessment.direct_supporter_identities == (
        left.identity,
        right.identity,
    )
    assert assessment.load_bearing_supporter_identities == (
        bottom.identity,
        left.identity,
        right.identity,
    )


def test_fragile_ancestor_on_any_support_branch_invalidates_configuration() -> None:
    safe_bottom = make_candidate(1, used_width_cm=5)
    fragile_bottom = make_candidate(
        2,
        position_x_cm=5,
        used_width_cm=5,
        fragile=True,
    )
    left = make_candidate(3, position_y_cm=10, used_width_cm=5)
    right = make_candidate(
        4,
        position_x_cm=5,
        position_y_cm=10,
        used_width_cm=5,
    )
    top = make_candidate(5, position_y_cm=20)

    assert not is_candidate_support_valid(
        top,
        [safe_bottom, fragile_bottom, left, right],
    )


def test_support_analysis_is_independent_of_input_order() -> None:
    bottom = make_candidate(30)
    middle = make_candidate(20, position_y_cm=10)
    top = make_candidate(10, position_y_cm=20)
    placements = [bottom, middle, top]

    assert analyze_support_configuration(placements) == (
        analyze_support_configuration(list(reversed(placements)))
    )


def test_support_validation_does_not_mutate_input() -> None:
    support = make_candidate(1)
    candidate = make_candidate(2, position_y_cm=10)
    placed_candidates = [support]
    original = list(placed_candidates)

    is_candidate_support_valid(candidate, placed_candidates)

    assert placed_candidates == original


def test_support_assessment_is_immutable() -> None:
    candidate = make_candidate(1)
    assessment = analyze_support_configuration([candidate])[0]

    with pytest.raises(FrozenInstanceError):
        assessment.supported_area_cm2 = 0


def test_candidate_validation_rechecks_the_entire_tentative_layout() -> None:
    floating = make_candidate(1, position_y_cm=10)
    candidate = make_candidate(2, position_x_cm=20)

    assert not is_candidate_support_valid(candidate, [floating])


def test_support_policy_composes_with_positioning_and_collision() -> None:
    support = make_candidate(1)
    placed_boxes = [support.box]
    selected = select_first_valid_candidate(
        make_candidate(2).volume,
        InternalDimensions(10, 20, 10),
        placed_boxes,
        validate_candidate=lambda candidate: (
            is_collision_free(
                candidate.box,
                placed_boxes,
            )
            and is_candidate_support_valid(candidate, [support])
        ),
    )

    assert selected.box == PositionedAABB(0, 10, 0, 10, 10, 10)


@pytest.mark.parametrize(
    ("field_name", "overrides"),
    [
        ("placements[0].volume.stackable", {"stackable": 1}),
        ("placements[0].volume.fragile", {"fragile": 0}),
        ("placements[0].volume.weight_kg", {"weight_kg": Decimal(0)}),
        ("placements[0].volume.weight_kg", {"weight_kg": Decimal("NaN")}),
        ("placements[0].volume.weight_kg", {"weight_kg": 1}),
    ],
)
def test_support_validation_rejects_invalid_physical_contracts(
    field_name: str,
    overrides: dict[str, object],
) -> None:
    with pytest.raises(InvalidSupportInputError) as exc_info:
        is_support_configuration_valid([make_candidate(1, **overrides)])

    assert exc_info.value.code == "INVALID_SUPPORT_INPUT"
    assert exc_info.value.field_name == field_name


@pytest.mark.parametrize(
    ("identity", "field_name"),
    [
        (
            VolumeIdentity(  # type: ignore[arg-type]
                order_item_id="invalid",
                volume_index=1,
            ),
            "placements[0].identity.order_item_id",
        ),
        (
            VolumeIdentity(order_item_id=UUID(int=1), volume_index=0),
            "placements[0].identity.volume_index",
        ),
        (
            VolumeIdentity(order_item_id=UUID(int=1), volume_index=True),
            "placements[0].identity.volume_index",
        ),
    ],
)
def test_support_validation_rejects_invalid_identity_contract(
    identity: VolumeIdentity,
    field_name: str,
) -> None:
    candidate = make_candidate(1)
    malformed = PlacementCandidate(
        volume=replace(candidate.volume, identity=identity),
        rotation=candidate.rotation,
        box=candidate.box,
    )

    with pytest.raises(InvalidSupportInputError) as exc_info:
        is_support_configuration_valid([malformed])

    assert exc_info.value.field_name == field_name


def test_candidate_validation_rejects_invalid_candidate() -> None:
    with pytest.raises(InvalidSupportInputError) as exc_info:
        is_candidate_support_valid(object(), [])  # type: ignore[arg-type]

    assert exc_info.value.field_name == "candidate"


def test_support_validation_rejects_unordered_collection() -> None:
    with pytest.raises(InvalidSupportInputError) as exc_info:
        is_support_configuration_valid({make_candidate(1)})  # type: ignore[arg-type]

    assert exc_info.value.field_name == "placements"


def test_support_validation_rejects_invalid_element_before_physical_result() -> None:
    with pytest.raises(InvalidSupportInputError) as exc_info:
        is_support_configuration_valid(  # type: ignore[list-item]
            [make_candidate(1, position_y_cm=10), object()]
        )

    assert exc_info.value.field_name == "placements[1]"


def test_support_validation_rejects_duplicate_identities() -> None:
    with pytest.raises(InvalidSupportInputError) as exc_info:
        is_support_configuration_valid([make_candidate(1), make_candidate(1)])

    assert exc_info.value.field_name == "placements"


def test_candidate_identity_must_not_duplicate_placed_candidate() -> None:
    with pytest.raises(InvalidSupportInputError) as exc_info:
        is_candidate_support_valid(make_candidate(1), [make_candidate(1)])

    assert exc_info.value.field_name == "candidate.identity"
