from dataclasses import dataclass
from enum import Enum

from app.modules.load_planning.optimizer.contracts import IndividualVolume


class RotationDomainError(ValueError):
    code: str


class InvalidRotationInputError(RotationDomainError):
    code = "INVALID_ROTATION_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class RotationCode(str, Enum):
    XYZ = "XYZ"
    XZY = "XZY"
    YXZ = "YXZ"
    YZX = "YZX"
    ZXY = "ZXY"
    ZYX = "ZYX"


@dataclass(frozen=True)
class RotationOption:
    rotation_code: RotationCode
    used_width_cm: int
    used_height_cm: int
    used_length_cm: int


_ROTATION_DEFINITIONS: tuple[tuple[RotationCode, tuple[int, int, int]], ...] = (
    (RotationCode.XYZ, (0, 1, 2)),
    (RotationCode.XZY, (0, 2, 1)),
    (RotationCode.YXZ, (1, 0, 2)),
    (RotationCode.YZX, (1, 2, 0)),
    (RotationCode.ZXY, (2, 0, 1)),
    (RotationCode.ZYX, (2, 1, 0)),
)


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InvalidRotationInputError(field_name, "must be a positive integer")


def generate_rotations(volume: IndividualVolume) -> tuple[RotationOption, ...]:
    if not isinstance(volume, IndividualVolume):
        raise InvalidRotationInputError("volume", "must be an IndividualVolume")

    dimensions = (
        volume.original_width_cm,
        volume.original_height_cm,
        volume.original_length_cm,
    )
    for field_name, value in zip(
        ("original_width_cm", "original_height_cm", "original_length_cm"),
        dimensions,
        strict=True,
    ):
        _require_positive_int(value, field_name)
    if not isinstance(volume.rotation_allowed, bool):
        raise InvalidRotationInputError("rotation_allowed", "must be a boolean")

    definitions = (
        _ROTATION_DEFINITIONS if volume.rotation_allowed else _ROTATION_DEFINITIONS[:1]
    )
    rotations: list[RotationOption] = []
    seen_dimensions: set[tuple[int, int, int]] = set()

    for rotation_code, axis_order in definitions:
        used_dimensions = tuple(dimensions[index] for index in axis_order)
        if used_dimensions in seen_dimensions:
            continue
        seen_dimensions.add(used_dimensions)
        rotations.append(
            RotationOption(
                rotation_code=rotation_code,
                used_width_cm=used_dimensions[0],
                used_height_cm=used_dimensions[1],
                used_length_cm=used_dimensions[2],
            )
        )

    return tuple(rotations)
