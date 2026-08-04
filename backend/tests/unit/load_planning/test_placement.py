from dataclasses import FrozenInstanceError
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
)
from app.modules.load_planning.optimizer.placement import (
    CandidatePoint,
    InvalidPlacementInputError,
    NoValidPositionError,
    PlacementCandidate,
    TruckDimensionsExceededError,
    generate_candidate_points,
    select_first_valid_candidate,
)
from app.modules.load_planning.optimizer.rotations import RotationCode


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


def make_box(**overrides: int) -> PositionedAABB:
    values = {
        "position_x_cm": 0,
        "position_y_cm": 0,
        "position_z_cm": 0,
        "used_width_cm": 10,
        "used_height_cm": 10,
        "used_length_cm": 10,
    }
    values.update(overrides)
    return PositionedAABB(**values)


def accept_candidate(_candidate: PlacementCandidate) -> bool:
    return True


def test_generate_candidate_points_starts_at_origin_for_empty_truck() -> None:
    assert generate_candidate_points([]) == (CandidatePoint(0, 0, 0),)


def test_generate_candidate_points_adds_positive_faces_in_scan_order() -> None:
    points = generate_candidate_points(
        [make_box(used_width_cm=10, used_height_cm=20, used_length_cm=30)]
    )

    assert points == (
        CandidatePoint(0, 0, 0),
        CandidatePoint(10, 0, 0),
        CandidatePoint(0, 0, 30),
        CandidatePoint(0, 20, 0),
    )


def test_candidate_points_are_deduplicated_and_input_order_independent() -> None:
    first = make_box()
    second = make_box(position_x_cm=10)
    expected = (
        CandidatePoint(0, 0, 0),
        CandidatePoint(10, 0, 0),
        CandidatePoint(20, 0, 0),
        CandidatePoint(0, 0, 10),
        CandidatePoint(10, 0, 10),
        CandidatePoint(0, 10, 0),
        CandidatePoint(10, 10, 0),
    )

    assert generate_candidate_points([first, second]) == expected
    assert generate_candidate_points([second, first]) == expected


def test_generate_candidate_points_does_not_mutate_input() -> None:
    placed_boxes = [make_box(), make_box(position_x_cm=10)]
    original = list(placed_boxes)

    generate_candidate_points(placed_boxes)

    assert placed_boxes == original


@pytest.mark.parametrize("invalid_value", [-1, True, 1.5])
def test_candidate_point_rejects_invalid_coordinates(
    invalid_value: object,
) -> None:
    with pytest.raises(InvalidPlacementInputError) as exc_info:
        CandidatePoint(invalid_value, 0, 0)  # type: ignore[arg-type]

    assert exc_info.value.field_name == "position_x_cm"


def test_select_candidate_uses_origin_and_original_rotation() -> None:
    volume = make_volume()
    candidate = select_first_valid_candidate(
        volume,
        InternalDimensions(100, 100, 100),
        [],
        validate_candidate=accept_candidate,
    )

    assert candidate.volume is volume
    assert candidate.identity == volume.identity
    assert candidate.box == PositionedAABB(0, 0, 0, 10, 20, 30)
    assert candidate.rotation_code is RotationCode.XYZ


def test_select_candidate_accepts_an_exact_fit() -> None:
    candidate = select_first_valid_candidate(
        make_volume(rotation_allowed=False),
        InternalDimensions(10, 20, 30),
        [],
        validate_candidate=accept_candidate,
    )

    assert candidate.box == PositionedAABB(0, 0, 0, 10, 20, 30)


def test_bounds_are_checked_before_the_validator() -> None:
    attempted: list[PlacementCandidate] = []

    def record_candidate(candidate: PlacementCandidate) -> bool:
        attempted.append(candidate)
        return True

    candidate = select_first_valid_candidate(
        make_volume(
            original_width_cm=6,
            original_height_cm=5,
            original_length_cm=4,
            volume_cm3=120,
        ),
        InternalDimensions(5, 6, 4),
        [],
        validate_candidate=record_candidate,
    )

    assert [item.rotation_code for item in attempted] == [RotationCode.YXZ]
    assert candidate.rotation_code is RotationCode.YXZ
    assert candidate.box == PositionedAABB(0, 0, 0, 5, 6, 4)


def test_candidate_point_precedes_rotation_rank_in_first_fit_order() -> None:
    attempted: list[tuple[int, RotationCode]] = []

    def accept_xzy_at_origin_or_xyz_later(candidate: PlacementCandidate) -> bool:
        attempted.append((candidate.position_x_cm, candidate.rotation_code))
        return (
            candidate.position_x_cm == 0 and candidate.rotation_code is RotationCode.XZY
        ) or (
            candidate.position_x_cm == 10
            and candidate.rotation_code is RotationCode.XYZ
        )

    candidate = select_first_valid_candidate(
        make_volume(),
        InternalDimensions(100, 100, 100),
        [make_box()],
        validate_candidate=accept_xzy_at_origin_or_xyz_later,
    )

    assert attempted == [(0, RotationCode.XYZ), (0, RotationCode.XZY)]
    assert candidate.position_x_cm == 0
    assert candidate.rotation_code is RotationCode.XZY


def test_selector_uses_official_rotation_order_at_each_point() -> None:
    attempted: list[RotationCode] = []

    def accept_third_rotation(candidate: PlacementCandidate) -> bool:
        attempted.append(candidate.rotation_code)
        return candidate.rotation_code is RotationCode.YXZ

    candidate = select_first_valid_candidate(
        make_volume(),
        InternalDimensions(100, 100, 100),
        [],
        validate_candidate=accept_third_rotation,
    )

    assert attempted == [RotationCode.XYZ, RotationCode.XZY, RotationCode.YXZ]
    assert candidate.rotation_code is RotationCode.YXZ


def test_selector_uses_frontier_from_multiple_preplaced_boxes() -> None:
    candidate = select_first_valid_candidate(
        make_volume(
            original_width_cm=10,
            original_height_cm=10,
            original_length_cm=10,
            volume_cm3=1_000,
        ),
        InternalDimensions(30, 10, 10),
        [make_box(), make_box(position_x_cm=10)],
        validate_candidate=lambda item: item.position_x_cm >= 20,
    )

    assert candidate.box == PositionedAABB(20, 0, 0, 10, 10, 10)


def test_selector_raises_stable_rejection_after_exhausting_candidates() -> None:
    volume = make_volume()
    attempted: list[PlacementCandidate] = []

    def reject_candidate(candidate: PlacementCandidate) -> bool:
        attempted.append(candidate)
        return False

    with pytest.raises(NoValidPositionError) as exc_info:
        select_first_valid_candidate(
            volume,
            InternalDimensions(100, 100, 100),
            [],
            validate_candidate=reject_candidate,
        )

    assert len(attempted) == 6
    assert exc_info.value.code == "NO_VALID_POSITION"
    assert exc_info.value.identity == volume.identity


def test_selector_rejects_volume_larger_than_every_orientation() -> None:
    volume = make_volume(
        original_width_cm=20,
        original_height_cm=30,
        original_length_cm=40,
        volume_cm3=24_000,
    )
    called = False

    def record_call(_candidate: PlacementCandidate) -> bool:
        nonlocal called
        called = True
        return True

    with pytest.raises(TruckDimensionsExceededError) as exc_info:
        select_first_valid_candidate(
            volume,
            InternalDimensions(10, 10, 10),
            [],
            validate_candidate=record_call,
        )

    assert not called
    assert exc_info.value.code == "TRUCK_DIMENSIONS_EXCEEDED"
    assert exc_info.value.identity == volume.identity


def test_placement_candidate_is_immutable() -> None:
    candidate = select_first_valid_candidate(
        make_volume(),
        InternalDimensions(100, 100, 100),
        [],
        validate_candidate=accept_candidate,
    )

    with pytest.raises(FrozenInstanceError):
        candidate.box = make_box()


def test_placement_candidate_requires_box_dimensions_to_match_rotation() -> None:
    candidate = select_first_valid_candidate(
        make_volume(),
        InternalDimensions(100, 100, 100),
        [],
        validate_candidate=accept_candidate,
    )

    with pytest.raises(InvalidPlacementInputError) as exc_info:
        PlacementCandidate(
            volume=candidate.volume,
            rotation=candidate.rotation,
            box=make_box(used_width_cm=99),
        )

    assert exc_info.value.field_name == "box"


def test_generate_candidate_points_rejects_unordered_collection() -> None:
    with pytest.raises(InvalidPlacementInputError) as exc_info:
        generate_candidate_points({make_box()})  # type: ignore[arg-type]

    assert exc_info.value.field_name == "placed_boxes"


def test_generate_candidate_points_rejects_invalid_element() -> None:
    with pytest.raises(InvalidPlacementInputError) as exc_info:
        generate_candidate_points([object()])  # type: ignore[list-item]

    assert exc_info.value.field_name == "placed_boxes[0]"


def test_selector_rejects_invalid_core_contracts() -> None:
    with pytest.raises(InvalidPlacementInputError) as volume_error:
        select_first_valid_candidate(  # type: ignore[arg-type]
            object(),
            InternalDimensions(100, 100, 100),
            [],
            validate_candidate=accept_candidate,
        )
    assert volume_error.value.field_name == "volume"

    with pytest.raises(InvalidPlacementInputError) as bounds_error:
        select_first_valid_candidate(  # type: ignore[arg-type]
            make_volume(),
            object(),
            [],
            validate_candidate=accept_candidate,
        )
    assert bounds_error.value.field_name == "bounds"


def test_selector_rejects_preplaced_box_outside_bounds() -> None:
    with pytest.raises(InvalidPlacementInputError) as exc_info:
        select_first_valid_candidate(
            make_volume(),
            InternalDimensions(100, 100, 100),
            [make_box(position_x_cm=91)],
            validate_candidate=accept_candidate,
        )

    assert exc_info.value.field_name == "placed_boxes[0]"


def test_selector_requires_callable_validator() -> None:
    with pytest.raises(InvalidPlacementInputError) as exc_info:
        select_first_valid_candidate(  # type: ignore[arg-type]
            make_volume(),
            InternalDimensions(100, 100, 100),
            [],
            validate_candidate=True,
        )

    assert exc_info.value.field_name == "validate_candidate"


def test_selector_requires_explicit_validator() -> None:
    with pytest.raises(TypeError, match="validate_candidate"):
        select_first_valid_candidate(  # type: ignore[call-arg]
            make_volume(),
            InternalDimensions(100, 100, 100),
            [],
        )


def test_selector_requires_validator_as_keyword_argument() -> None:
    with pytest.raises(TypeError):
        select_first_valid_candidate(  # type: ignore[call-arg]
            make_volume(),
            InternalDimensions(100, 100, 100),
            [],
            accept_candidate,
        )


def test_selector_requires_boolean_validator_result() -> None:
    with pytest.raises(InvalidPlacementInputError) as exc_info:
        select_first_valid_candidate(
            make_volume(),
            InternalDimensions(100, 100, 100),
            [],
            validate_candidate=lambda _candidate: 1,  # type: ignore[return-value]
        )

    assert exc_info.value.field_name == "validate_candidate"


def test_selector_propagates_validator_exception() -> None:
    expected_error = RuntimeError("validator unavailable")

    def raise_expected_error(_candidate: PlacementCandidate) -> bool:
        raise expected_error

    with pytest.raises(RuntimeError) as exc_info:
        select_first_valid_candidate(
            make_volume(),
            InternalDimensions(100, 100, 100),
            [],
            validate_candidate=raise_expected_error,
        )

    assert exc_info.value is expected_error
