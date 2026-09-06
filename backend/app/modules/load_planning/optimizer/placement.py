from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.geometry import (
    InternalDimensions,
    PositionedAABB,
    fits_within_bounds,
)
from app.modules.load_planning.optimizer.rejections import RejectionReason
from app.modules.load_planning.optimizer.rotations import (
    RotationCode,
    RotationOption,
    generate_rotations,
)


class PlacementDomainError(ValueError):
    code: str


class InvalidPlacementInputError(PlacementDomainError):
    code = "INVALID_PLACEMENT_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class NoValidPositionError(PlacementDomainError):
    code = RejectionReason.NO_VALID_POSITION.value

    def __init__(self, identity: VolumeIdentity) -> None:
        self.identity = identity
        super().__init__(
            "no valid position for volume "
            f"({identity.order_item_id}, {identity.volume_index})"
        )


class TruckDimensionsExceededError(PlacementDomainError):
    code = RejectionReason.TRUCK_DIMENSIONS_EXCEEDED.value

    def __init__(self, identity: VolumeIdentity) -> None:
        self.identity = identity
        super().__init__(
            "all allowed rotations exceed truck dimensions for volume "
            f"({identity.order_item_id}, {identity.volume_index})"
        )


def _validate_non_negative_coordinate(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidPlacementInputError(field_name, "must be a non-negative integer")


@dataclass(frozen=True)
class CandidatePoint:
    position_x_cm: int
    position_y_cm: int
    position_z_cm: int

    def __post_init__(self) -> None:
        _validate_non_negative_coordinate(self.position_x_cm, "position_x_cm")
        _validate_non_negative_coordinate(self.position_y_cm, "position_y_cm")
        _validate_non_negative_coordinate(self.position_z_cm, "position_z_cm")


@dataclass(frozen=True)
class PlacementCandidate:
    """Provisional placement awaiting all physical validators."""

    volume: IndividualVolume
    rotation: RotationOption
    box: PositionedAABB

    def __post_init__(self) -> None:
        if not isinstance(self.volume, IndividualVolume):
            raise InvalidPlacementInputError("volume", "must be an IndividualVolume")
        if not isinstance(self.rotation, RotationOption):
            raise InvalidPlacementInputError("rotation", "must be a RotationOption")
        if not isinstance(self.box, PositionedAABB):
            raise InvalidPlacementInputError("box", "must be a PositionedAABB")

        rotation_dimensions = (
            self.rotation.used_width_cm,
            self.rotation.used_height_cm,
            self.rotation.used_length_cm,
        )
        box_dimensions = (
            self.box.used_width_cm,
            self.box.used_height_cm,
            self.box.used_length_cm,
        )
        if box_dimensions != rotation_dimensions:
            raise InvalidPlacementInputError(
                "box", "dimensions must match the selected rotation"
            )

    @property
    def identity(self) -> VolumeIdentity:
        return self.volume.identity

    @property
    def position_x_cm(self) -> int:
        return self.box.position_x_cm

    @property
    def position_y_cm(self) -> int:
        return self.box.position_y_cm

    @property
    def position_z_cm(self) -> int:
        return self.box.position_z_cm

    @property
    def used_width_cm(self) -> int:
        return self.box.used_width_cm

    @property
    def used_height_cm(self) -> int:
        return self.box.used_height_cm

    @property
    def used_length_cm(self) -> int:
        return self.box.used_length_cm

    @property
    def rotation_code(self) -> RotationCode:
        return self.rotation.rotation_code


CandidateValidator = Callable[[PlacementCandidate], bool]


def _validate_placed_boxes(
    placed_boxes: Sequence[PositionedAABB],
) -> tuple[PositionedAABB, ...]:
    if not isinstance(placed_boxes, Sequence) or isinstance(
        placed_boxes, (str, bytes, bytearray)
    ):
        raise InvalidPlacementInputError(
            "placed_boxes", "must be an ordered sequence of PositionedAABB"
        )

    validated = tuple(placed_boxes)
    for position, box in enumerate(validated):
        if not isinstance(box, PositionedAABB):
            raise InvalidPlacementInputError(
                f"placed_boxes[{position}]", "must be a PositionedAABB"
            )
    return validated


def generate_candidate_points(
    placed_boxes: Sequence[PositionedAABB],
) -> tuple[CandidatePoint, ...]:
    validated_boxes = _validate_placed_boxes(placed_boxes)
    points = {CandidatePoint(0, 0, 0)}

    for box in validated_boxes:
        points.update(
            (
                CandidatePoint(
                    box.position_x_cm + box.used_width_cm,
                    box.position_y_cm,
                    box.position_z_cm,
                ),
                CandidatePoint(
                    box.position_x_cm,
                    box.position_y_cm + box.used_height_cm,
                    box.position_z_cm,
                ),
                CandidatePoint(
                    box.position_x_cm,
                    box.position_y_cm,
                    box.position_z_cm + box.used_length_cm,
                ),
            )
        )

    return tuple(
        sorted(
            points,
            key=lambda point: (
                point.position_y_cm,
                point.position_z_cm,
                point.position_x_cm,
            ),
        )
    )


def select_first_valid_candidate(
    volume: IndividualVolume,
    bounds: InternalDimensions,
    placed_boxes: Sequence[PositionedAABB],
    *,
    validate_candidate: CandidateValidator,
) -> PlacementCandidate:
    if not isinstance(volume, IndividualVolume):
        raise InvalidPlacementInputError("volume", "must be an IndividualVolume")
    if not isinstance(bounds, InternalDimensions):
        raise InvalidPlacementInputError("bounds", "must be InternalDimensions")
    if not callable(validate_candidate):
        raise InvalidPlacementInputError("validate_candidate", "must be callable")

    validated_boxes = _validate_placed_boxes(placed_boxes)
    for position, box in enumerate(validated_boxes):
        if not fits_within_bounds(box, bounds):
            raise InvalidPlacementInputError(
                f"placed_boxes[{position}]", "must fit within bounds"
            )

    rotations = generate_rotations(volume)
    if not any(
        rotation.used_width_cm <= bounds.internal_width_cm
        and rotation.used_height_cm <= bounds.internal_height_cm
        and rotation.used_length_cm <= bounds.internal_length_cm
        for rotation in rotations
    ):
        raise TruckDimensionsExceededError(volume.identity)

    for point in generate_candidate_points(validated_boxes):
        for rotation in rotations:
            box = PositionedAABB(
                position_x_cm=point.position_x_cm,
                position_y_cm=point.position_y_cm,
                position_z_cm=point.position_z_cm,
                used_width_cm=rotation.used_width_cm,
                used_height_cm=rotation.used_height_cm,
                used_length_cm=rotation.used_length_cm,
            )
            if not fits_within_bounds(box, bounds):
                continue

            candidate = PlacementCandidate(
                volume=volume,
                rotation=rotation,
                box=box,
            )
            candidate_is_valid = validate_candidate(candidate)
            if not isinstance(candidate_is_valid, bool):
                raise InvalidPlacementInputError(
                    "validate_candidate", "must return a boolean"
                )
            if candidate_is_valid:
                return candidate

    raise NoValidPositionError(volume.identity)
