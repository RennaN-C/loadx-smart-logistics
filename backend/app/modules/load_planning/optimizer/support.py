from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise
from uuid import UUID

from app.modules.load_planning.optimizer.contracts import VolumeIdentity
from app.modules.load_planning.optimizer.placement import PlacementCandidate


class SupportDomainError(ValueError):
    code: str


class InvalidSupportInputError(SupportDomainError):
    code = "INVALID_SUPPORT_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


@dataclass(frozen=True)
class SupportAssessment:
    identity: VolumeIdentity
    on_floor: bool
    base_area_cm2: int
    supported_area_cm2: int
    direct_supporter_identities: tuple[VolumeIdentity, ...]
    load_bearing_supporter_identities: tuple[VolumeIdentity, ...]

    @property
    def is_fully_supported(self) -> bool:
        return self.supported_area_cm2 == self.base_area_cm2


@dataclass(frozen=True)
class _ContactRectangleXZ:
    min_x_cm: int
    max_x_cm: int
    min_z_cm: int
    max_z_cm: int


def _identity_key(identity: VolumeIdentity) -> tuple[int, int]:
    return (identity.order_item_id.int, identity.volume_index)


def _validate_placement(placement: object, field_name: str) -> PlacementCandidate:
    if not isinstance(placement, PlacementCandidate):
        raise InvalidSupportInputError(field_name, "must be a PlacementCandidate")

    identity = placement.identity
    if not isinstance(identity, VolumeIdentity):
        raise InvalidSupportInputError(
            f"{field_name}.identity", "must be a VolumeIdentity"
        )
    if not isinstance(identity.order_item_id, UUID):
        raise InvalidSupportInputError(
            f"{field_name}.identity.order_item_id", "must be a UUID"
        )
    if (
        not isinstance(identity.volume_index, int)
        or isinstance(identity.volume_index, bool)
        or identity.volume_index <= 0
    ):
        raise InvalidSupportInputError(
            f"{field_name}.identity.volume_index",
            "must be a positive integer",
        )

    for flag_name in ("stackable", "fragile"):
        if not isinstance(getattr(placement.volume, flag_name), bool):
            raise InvalidSupportInputError(
                f"{field_name}.volume.{flag_name}", "must be a boolean"
            )

    weight_kg = placement.volume.weight_kg
    if not isinstance(weight_kg, Decimal):
        raise InvalidSupportInputError(
            f"{field_name}.volume.weight_kg", "must be a Decimal"
        )
    if not weight_kg.is_finite() or weight_kg <= 0:
        raise InvalidSupportInputError(
            f"{field_name}.volume.weight_kg",
            "must be finite and greater than zero",
        )
    return placement


def _validate_placements(
    placements: Sequence[PlacementCandidate],
    field_name: str,
) -> tuple[PlacementCandidate, ...]:
    if not isinstance(placements, Sequence) or isinstance(
        placements, (str, bytes, bytearray)
    ):
        raise InvalidSupportInputError(
            field_name, "must be an ordered sequence of PlacementCandidate"
        )

    validated = tuple(placements)
    for position, placement in enumerate(validated):
        _validate_placement(placement, f"{field_name}[{position}]")
    return validated


def _ensure_unique_identities(
    placements: tuple[PlacementCandidate, ...],
    field_name: str,
) -> None:
    seen: set[VolumeIdentity] = set()
    for placement in placements:
        if placement.identity in seen:
            raise InvalidSupportInputError(
                field_name, "must contain unique volume identities"
            )
        seen.add(placement.identity)


def _contact_rectangle(
    upper: PlacementCandidate,
    lower: PlacementCandidate,
) -> _ContactRectangleXZ | None:
    if lower.position_y_cm + lower.used_height_cm != upper.position_y_cm:
        return None

    min_x_cm = max(upper.position_x_cm, lower.position_x_cm)
    max_x_cm = min(
        upper.position_x_cm + upper.used_width_cm,
        lower.position_x_cm + lower.used_width_cm,
    )
    min_z_cm = max(upper.position_z_cm, lower.position_z_cm)
    max_z_cm = min(
        upper.position_z_cm + upper.used_length_cm,
        lower.position_z_cm + lower.used_length_cm,
    )
    if min_x_cm >= max_x_cm or min_z_cm >= max_z_cm:
        return None
    return _ContactRectangleXZ(min_x_cm, max_x_cm, min_z_cm, max_z_cm)


def _merged_interval_length(intervals: list[tuple[int, int]]) -> int:
    if not intervals:
        return 0

    intervals.sort()
    current_start, current_end = intervals[0]
    total_length_cm = 0
    for interval_start, interval_end in intervals[1:]:
        if interval_start > current_end:
            total_length_cm += current_end - current_start
            current_start, current_end = interval_start, interval_end
            continue
        current_end = max(current_end, interval_end)
    return total_length_cm + current_end - current_start


def _union_area_cm2(rectangles: tuple[_ContactRectangleXZ, ...]) -> int:
    if not rectangles:
        return 0

    x_boundaries_cm = sorted(
        {
            boundary
            for rectangle in rectangles
            for boundary in (rectangle.min_x_cm, rectangle.max_x_cm)
        }
    )
    area_cm2 = 0
    for min_x_cm, max_x_cm in pairwise(x_boundaries_cm):
        z_intervals = [
            (rectangle.min_z_cm, rectangle.max_z_cm)
            for rectangle in rectangles
            if rectangle.min_x_cm < max_x_cm and rectangle.max_x_cm > min_x_cm
        ]
        area_cm2 += (max_x_cm - min_x_cm) * _merged_interval_length(z_intervals)
    return area_cm2


def _analyze_validated_configuration(
    placements: tuple[PlacementCandidate, ...],
) -> tuple[SupportAssessment, ...]:
    direct_supporters: dict[VolumeIdentity, tuple[PlacementCandidate, ...]] = {}
    supported_areas_cm2: dict[VolumeIdentity, int] = {}

    for upper in placements:
        base_area_cm2 = upper.used_width_cm * upper.used_length_cm
        if upper.position_y_cm == 0:
            direct_supporters[upper.identity] = ()
            supported_areas_cm2[upper.identity] = base_area_cm2
            continue

        contacts = tuple(
            (lower, rectangle)
            for lower in placements
            if lower.identity != upper.identity
            if (rectangle := _contact_rectangle(upper, lower)) is not None
        )
        direct_supporters[upper.identity] = tuple(
            lower for lower, _rectangle in contacts
        )
        supported_areas_cm2[upper.identity] = _union_area_cm2(
            tuple(rectangle for _lower, rectangle in contacts)
        )

    assessments: list[SupportAssessment] = []
    for placement in placements:
        direct_identities = {
            supporter.identity for supporter in direct_supporters[placement.identity]
        }
        load_bearing_identities = set(direct_identities)
        pending = list(direct_identities)
        while pending:
            supporter_identity = pending.pop()
            for ancestor in direct_supporters[supporter_identity]:
                if ancestor.identity in load_bearing_identities:
                    continue
                load_bearing_identities.add(ancestor.identity)
                pending.append(ancestor.identity)

        base_area_cm2 = placement.used_width_cm * placement.used_length_cm
        assessments.append(
            SupportAssessment(
                identity=placement.identity,
                on_floor=placement.position_y_cm == 0,
                base_area_cm2=base_area_cm2,
                supported_area_cm2=supported_areas_cm2[placement.identity],
                direct_supporter_identities=tuple(
                    sorted(direct_identities, key=_identity_key)
                ),
                load_bearing_supporter_identities=tuple(
                    sorted(load_bearing_identities, key=_identity_key)
                ),
            )
        )
    return tuple(sorted(assessments, key=lambda item: _identity_key(item.identity)))


def _is_validated_configuration_valid(
    placements: tuple[PlacementCandidate, ...],
) -> bool:
    placements_by_identity = {placement.identity: placement for placement in placements}
    for assessment in _analyze_validated_configuration(placements):
        if not assessment.is_fully_supported:
            return False
        if any(
            not placements_by_identity[identity].volume.stackable
            for identity in assessment.direct_supporter_identities
        ):
            return False
        if any(
            placements_by_identity[identity].volume.fragile
            for identity in assessment.load_bearing_supporter_identities
        ):
            return False
    return True


def analyze_support_configuration(
    placements: Sequence[PlacementCandidate],
) -> tuple[SupportAssessment, ...]:
    validated = _validate_placements(placements, "placements")
    _ensure_unique_identities(validated, "placements")
    return _analyze_validated_configuration(validated)


def is_support_configuration_valid(
    placements: Sequence[PlacementCandidate],
) -> bool:
    validated = _validate_placements(placements, "placements")
    _ensure_unique_identities(validated, "placements")
    return _is_validated_configuration_valid(validated)


def is_candidate_support_valid(
    candidate: PlacementCandidate,
    placed_candidates: Sequence[PlacementCandidate],
) -> bool:
    validated_candidate = _validate_placement(candidate, "candidate")
    validated_placed = _validate_placements(placed_candidates, "placed_candidates")
    _ensure_unique_identities(validated_placed, "placed_candidates")
    if any(
        placement.identity == validated_candidate.identity
        for placement in validated_placed
    ):
        raise InvalidSupportInputError(
            "candidate.identity",
            "must not duplicate a placed candidate identity",
        )
    return _is_validated_configuration_valid((*validated_placed, validated_candidate))
