from dataclasses import FrozenInstanceError

import pytest

from app.modules.load_planning.optimizer.geometry import (
    AABBRelation,
    InternalDimensions,
    InvalidGeometryInputError,
    PositionedAABB,
    classify_aabb_relation,
    fits_within_bounds,
    is_collision_free,
)


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


def test_geometry_contracts_are_immutable() -> None:
    bounds = InternalDimensions(100, 100, 100)
    box = make_box()

    with pytest.raises(FrozenInstanceError):
        bounds.internal_width_cm = 200
    with pytest.raises(FrozenInstanceError):
        box.position_x_cm = 1


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("internal_width_cm", 0),
        ("internal_width_cm", -1),
        ("internal_height_cm", 0),
        ("internal_height_cm", -1),
        ("internal_length_cm", 0),
        ("internal_length_cm", -1),
    ],
)
def test_internal_dimensions_reject_non_positive_values(
    field_name: str,
    invalid_value: int,
) -> None:
    values = {
        "internal_width_cm": 100,
        "internal_height_cm": 100,
        "internal_length_cm": 100,
    }
    values[field_name] = invalid_value

    with pytest.raises(InvalidGeometryInputError) as exc_info:
        InternalDimensions(**values)

    assert exc_info.value.code == "INVALID_GEOMETRY_INPUT"
    assert exc_info.value.field_name == field_name


@pytest.mark.parametrize(
    "field_name",
    ["used_width_cm", "used_height_cm", "used_length_cm"],
)
@pytest.mark.parametrize("invalid_value", [0, -1])
def test_positioned_aabb_rejects_non_positive_dimensions(
    field_name: str,
    invalid_value: int,
) -> None:
    with pytest.raises(InvalidGeometryInputError) as exc_info:
        make_box(**{field_name: invalid_value})

    assert exc_info.value.code == "INVALID_GEOMETRY_INPUT"
    assert exc_info.value.field_name == field_name


@pytest.mark.parametrize(
    "field_name",
    ["position_x_cm", "position_y_cm", "position_z_cm"],
)
def test_positioned_aabb_rejects_negative_coordinates(field_name: str) -> None:
    with pytest.raises(InvalidGeometryInputError) as exc_info:
        make_box(**{field_name: -1})

    assert exc_info.value.code == "INVALID_GEOMETRY_INPUT"
    assert exc_info.value.field_name == field_name


def test_box_at_origin_fits_within_bounds() -> None:
    assert fits_within_bounds(
        make_box(),
        InternalDimensions(100, 100, 100),
    )


def test_box_on_exact_positive_boundaries_fits_within_bounds() -> None:
    box = make_box(position_x_cm=90, position_y_cm=90, position_z_cm=90)

    assert fits_within_bounds(box, InternalDimensions(100, 100, 100))


@pytest.mark.parametrize(
    "coordinate_override",
    [
        {"position_x_cm": 91},
        {"position_y_cm": 91},
        {"position_z_cm": 91},
    ],
)
def test_box_exceeding_any_axis_does_not_fit(
    coordinate_override: dict[str, int],
) -> None:
    assert not fits_within_bounds(
        make_box(**coordinate_override),
        InternalDimensions(100, 100, 100),
    )


def test_box_larger_than_bounds_does_not_fit() -> None:
    assert not fits_within_bounds(
        make_box(used_width_cm=101),
        InternalDimensions(100, 100, 100),
    )


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (make_box(), make_box()),
        (make_box(), make_box(position_x_cm=5, position_y_cm=5, position_z_cm=5)),
        (
            make_box(used_width_cm=20, used_height_cm=20, used_length_cm=20),
            make_box(position_x_cm=5, position_y_cm=5, position_z_cm=5),
        ),
        (
            make_box(position_x_cm=5, position_y_cm=5, position_z_cm=5),
            make_box(used_width_cm=20, used_height_cm=20, used_length_cm=20),
        ),
    ],
)
def test_classifies_total_partial_and_contained_overlap_as_positive(
    first: PositionedAABB,
    second: PositionedAABB,
) -> None:
    assert classify_aabb_relation(first, second) is AABBRelation.POSITIVE_OVERLAP


@pytest.mark.parametrize(
    "second",
    [
        make_box(position_x_cm=11),
        make_box(position_y_cm=11),
        make_box(position_z_cm=11),
    ],
)
def test_classifies_boxes_with_a_gap_as_separated(second: PositionedAABB) -> None:
    assert classify_aabb_relation(make_box(), second) is AABBRelation.SEPARATED


@pytest.mark.parametrize(
    "second",
    [
        make_box(position_x_cm=10),
        make_box(position_x_cm=10, position_y_cm=10),
        make_box(position_x_cm=10, position_y_cm=10, position_z_cm=10),
    ],
)
def test_classifies_face_edge_and_vertex_contact_as_touching(
    second: PositionedAABB,
) -> None:
    assert classify_aabb_relation(make_box(), second) is AABBRelation.TOUCHING


@pytest.mark.parametrize(
    "relation",
    [
        (make_box(), make_box(position_x_cm=11)),
        (make_box(), make_box(position_x_cm=10)),
        (make_box(), make_box(position_x_cm=5)),
    ],
)
def test_aabb_relation_is_symmetric_and_deterministic(
    relation: tuple[PositionedAABB, PositionedAABB],
) -> None:
    first, second = relation
    expected = classify_aabb_relation(first, second)

    assert classify_aabb_relation(second, first) is expected
    assert classify_aabb_relation(first, second) is expected


def test_empty_truck_is_collision_free() -> None:
    assert is_collision_free(make_box(), [])


@pytest.mark.parametrize(
    "placed_box",
    [
        make_box(position_x_cm=10),
        make_box(position_y_cm=10),
        make_box(position_z_cm=10),
        make_box(position_x_cm=10, position_y_cm=10),
        make_box(position_x_cm=10, position_y_cm=10, position_z_cm=10),
    ],
)
def test_face_edge_and_vertex_contact_are_collision_free(
    placed_box: PositionedAABB,
) -> None:
    assert is_collision_free(make_box(), [placed_box])


@pytest.mark.parametrize(
    "placed_box",
    [
        make_box(),
        make_box(position_x_cm=9),
        make_box(position_x_cm=5, position_y_cm=5, position_z_cm=5),
        make_box(used_width_cm=20, used_height_cm=20, used_length_cm=20),
    ],
)
def test_positive_overlap_is_a_collision(
    placed_box: PositionedAABB,
) -> None:
    assert not is_collision_free(make_box(), [placed_box])


@pytest.mark.parametrize(
    "placed_box",
    [
        make_box(position_x_cm=11),
        make_box(position_y_cm=11),
        make_box(position_z_cm=11),
    ],
)
def test_one_centimeter_gap_is_collision_free_with_zero_tolerance(
    placed_box: PositionedAABB,
) -> None:
    assert is_collision_free(make_box(), [placed_box])


def test_candidate_is_checked_against_every_preplaced_box() -> None:
    placed_boxes = [
        make_box(position_x_cm=20),
        make_box(position_x_cm=10),
        make_box(position_x_cm=9),
    ]

    assert not is_collision_free(make_box(), placed_boxes)


def test_multiple_separated_and_touching_boxes_are_collision_free() -> None:
    placed_boxes = [
        make_box(position_x_cm=10),
        make_box(position_y_cm=20),
        make_box(position_z_cm=30),
    ]

    assert is_collision_free(make_box(), placed_boxes)


def test_collision_result_is_independent_of_preplaced_box_order() -> None:
    placed_boxes = [
        make_box(position_x_cm=20),
        make_box(position_x_cm=10),
        make_box(position_x_cm=9),
    ]

    assert not is_collision_free(make_box(), placed_boxes)
    assert not is_collision_free(make_box(), list(reversed(placed_boxes)))


def test_collision_check_does_not_mutate_input() -> None:
    placed_boxes = [make_box(position_x_cm=10), make_box(position_x_cm=20)]
    original = list(placed_boxes)

    is_collision_free(make_box(), placed_boxes)

    assert placed_boxes == original


def test_collision_check_rejects_invalid_candidate() -> None:
    with pytest.raises(InvalidGeometryInputError) as exc_info:
        is_collision_free(object(), [])  # type: ignore[arg-type]

    assert exc_info.value.code == "INVALID_GEOMETRY_INPUT"
    assert exc_info.value.field_name == "candidate_box"


def test_collision_check_rejects_unordered_collection() -> None:
    with pytest.raises(InvalidGeometryInputError) as exc_info:
        is_collision_free(make_box(), {make_box(position_x_cm=10)})  # type: ignore[arg-type]

    assert exc_info.value.field_name == "placed_boxes"


def test_collision_check_rejects_invalid_preplaced_box() -> None:
    with pytest.raises(InvalidGeometryInputError) as exc_info:
        is_collision_free(make_box(), [object()])  # type: ignore[list-item]

    assert exc_info.value.field_name == "placed_boxes[0]"


def test_invalid_preplaced_box_is_not_masked_by_an_earlier_collision() -> None:
    with pytest.raises(InvalidGeometryInputError) as exc_info:
        is_collision_free(
            make_box(),
            [make_box(), object()],  # type: ignore[list-item]
        )

    assert exc_info.value.field_name == "placed_boxes[1]"
