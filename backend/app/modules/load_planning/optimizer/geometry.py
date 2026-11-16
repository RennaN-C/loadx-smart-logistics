from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import Enum


class GeometryDomainError(ValueError):
    code: str


class InvalidGeometryInputError(GeometryDomainError):
    code = "INVALID_GEOMETRY_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class AABBRelation(str, Enum):
    SEPARATED = "SEPARATED"
    TOUCHING = "TOUCHING"
    POSITIVE_OVERLAP = "POSITIVE_OVERLAP"


def _validate_positive_cm(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InvalidGeometryInputError(field_name, "must be a positive integer")


def _validate_non_negative_cm(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidGeometryInputError(field_name, "must be a non-negative integer")


@dataclass(frozen=True)
class InternalDimensions:
    internal_width_cm: int
    internal_height_cm: int
    internal_length_cm: int

    def __post_init__(self) -> None:
        _validate_positive_cm(self.internal_width_cm, "internal_width_cm")
        _validate_positive_cm(self.internal_height_cm, "internal_height_cm")
        _validate_positive_cm(self.internal_length_cm, "internal_length_cm")


@dataclass(frozen=True)
class PositionedAABB:
    position_x_cm: int
    position_y_cm: int
    position_z_cm: int
    used_width_cm: int
    used_height_cm: int
    used_length_cm: int

    def __post_init__(self) -> None:
        _validate_non_negative_cm(self.position_x_cm, "position_x_cm")
        _validate_non_negative_cm(self.position_y_cm, "position_y_cm")
        _validate_non_negative_cm(self.position_z_cm, "position_z_cm")
        _validate_positive_cm(self.used_width_cm, "used_width_cm")
        _validate_positive_cm(self.used_height_cm, "used_height_cm")
        _validate_positive_cm(self.used_length_cm, "used_length_cm")


def fits_within_bounds(box: PositionedAABB, bounds: InternalDimensions) -> bool:
    return (
        box.position_x_cm + box.used_width_cm <= bounds.internal_width_cm
        and box.position_y_cm + box.used_height_cm <= bounds.internal_height_cm
        and box.position_z_cm + box.used_length_cm <= bounds.internal_length_cm
    )


def classify_aabb_relation(
    first: PositionedAABB, second: PositionedAABB
) -> AABBRelation:
    overlap_x_cm = min(
        first.position_x_cm + first.used_width_cm,
        second.position_x_cm + second.used_width_cm,
    ) - max(first.position_x_cm, second.position_x_cm)
    overlap_y_cm = min(
        first.position_y_cm + first.used_height_cm,
        second.position_y_cm + second.used_height_cm,
    ) - max(first.position_y_cm, second.position_y_cm)
    overlap_z_cm = min(
        first.position_z_cm + first.used_length_cm,
        second.position_z_cm + second.used_length_cm,
    ) - max(first.position_z_cm, second.position_z_cm)

    overlap_extents_cm = (overlap_x_cm, overlap_y_cm, overlap_z_cm)
    if any(extent_cm < 0 for extent_cm in overlap_extents_cm):
        return AABBRelation.SEPARATED
    if all(extent_cm > 0 for extent_cm in overlap_extents_cm):
        return AABBRelation.POSITIVE_OVERLAP
    return AABBRelation.TOUCHING


def is_collision_free(
    candidate_box: PositionedAABB,
    placed_boxes: Sequence[PositionedAABB],
) -> bool:
    if not isinstance(candidate_box, PositionedAABB):
        raise InvalidGeometryInputError("candidate_box", "must be a PositionedAABB")
    if not isinstance(placed_boxes, Sequence) or isinstance(
        placed_boxes, (str, bytes, bytearray)
    ):
        raise InvalidGeometryInputError(
            "placed_boxes", "must be an ordered sequence of PositionedAABB"
        )

    validated_boxes = tuple(placed_boxes)
    for position, box in enumerate(validated_boxes):
        if not isinstance(box, PositionedAABB):
            raise InvalidGeometryInputError(
                f"placed_boxes[{position}]", "must be a PositionedAABB"
            )

    return all(
        classify_aabb_relation(candidate_box, box) is not AABBRelation.POSITIVE_OVERLAP
        for box in validated_boxes
    )


class _CollisionIndex:
    """Exact broad phase for the engine's validated, append-only prefix.

    At most eight cells per axis, independent of centimetre dimensions. Cell
    membership only narrows the search; the existing AABB predicate decides.
    Half-open integer intervals keep face/edge contact out of adjacent cells.
    The public validator and final revalidation do not use this index.
    """

    def __init__(self, bounds: InternalDimensions) -> None:
        self._cell_sizes = tuple(
            max(1, (dimension + 7) // 8)
            for dimension in (
                bounds.internal_width_cm,
                bounds.internal_height_cm,
                bounds.internal_length_cm,
            )
        )
        self._cells: dict[tuple[int, int, int], list[int]] = {}
        self._boxes: list[PositionedAABB] = []

    def _keys(self, box: PositionedAABB) -> Iterator[tuple[int, int, int]]:
        sx, sy, sz = self._cell_sizes
        for x in range(
            box.position_x_cm // sx,
            (box.position_x_cm + box.used_width_cm - 1) // sx + 1,
        ):
            for y in range(
                box.position_y_cm // sy,
                (box.position_y_cm + box.used_height_cm - 1) // sy + 1,
            ):
                for z in range(
                    box.position_z_cm // sz,
                    (box.position_z_cm + box.used_length_cm - 1) // sz + 1,
                ):
                    yield x, y, z

    def add(self, box: PositionedAABB) -> None:
        index = len(self._boxes)
        self._boxes.append(box)
        for key in self._keys(box):
            self._cells.setdefault(key, []).append(index)

    def is_collision_free(self, candidate_box: PositionedAABB) -> bool:
        seen: set[int] = set()
        for key in self._keys(candidate_box):
            for index in self._cells.get(key, ()):
                if index in seen:
                    continue
                seen.add(index)
                if (
                    classify_aabb_relation(candidate_box, self._boxes[index])
                    is AABBRelation.POSITIVE_OVERLAP
                ):
                    return False
        return True
