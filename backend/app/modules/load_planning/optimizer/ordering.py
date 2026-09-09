from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)

VolumeOrderingKey = tuple[int, Decimal, int, int, int, int, int]


class VolumeOrderingError(ValueError):
    code: str


class InvalidVolumeOrderingInputError(VolumeOrderingError):
    code = "INVALID_VOLUME_ORDERING_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class DuplicateVolumeIdentityError(VolumeOrderingError):
    code = "DUPLICATE_VOLUME_IDENTITY"

    def __init__(self, identity: VolumeIdentity) -> None:
        self.identity = identity
        super().__init__(
            "volume identity "
            f"({identity.order_item_id}, {identity.volume_index}) appears more than once"
        )


def _raise_invalid(field_name: str, reason: str) -> None:
    raise InvalidVolumeOrderingInputError(field_name, reason)


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _raise_invalid(field_name, "must be a positive integer")


def _validate_ordering_fields(volume: IndividualVolume, position: int) -> None:
    prefix = f"volumes[{position}]"
    if not isinstance(volume.identity, VolumeIdentity):
        _raise_invalid(f"{prefix}.identity", "must be a VolumeIdentity")
    if not isinstance(volume.order_item_id, UUID):
        _raise_invalid(f"{prefix}.order_item_id", "must be a UUID")
    _require_positive_int(volume.volume_index, f"{prefix}.volume_index")
    _require_positive_int(volume.volume_cm3, f"{prefix}.volume_cm3")
    _require_positive_int(
        volume.delivery_sequence,
        f"{prefix}.delivery_sequence",
    )
    if (
        not isinstance(volume.weight_kg, Decimal)
        or not volume.weight_kg.is_finite()
        or volume.weight_kg <= 0
    ):
        _raise_invalid(f"{prefix}.weight_kg", "must be a positive finite Decimal")
    for field_name in ("stackable", "fragile"):
        if not isinstance(getattr(volume, field_name), bool):
            _raise_invalid(f"{prefix}.{field_name}", "must be a boolean")


def _ordering_key(volume: IndividualVolume) -> VolumeOrderingKey:
    return (
        -volume.volume_cm3,
        -volume.weight_kg,
        0 if not volume.stackable else 1,
        0 if not volume.fragile else 1,
        -volume.delivery_sequence,
        volume.order_item_id.int,
        volume.volume_index,
    )


def order_volumes(
    volumes: Sequence[IndividualVolume],
) -> tuple[IndividualVolume, ...]:
    if not isinstance(volumes, Sequence) or isinstance(
        volumes, (str, bytes, bytearray)
    ):
        raise InvalidVolumeOrderingInputError(
            "volumes", "must be an ordered sequence of IndividualVolume"
        )

    ordered_input = tuple(volumes)
    seen_identities: set[VolumeIdentity] = set()
    for position, volume in enumerate(ordered_input):
        if not isinstance(volume, IndividualVolume):
            raise InvalidVolumeOrderingInputError(
                f"volumes[{position}]", "must be an IndividualVolume"
            )
        _validate_ordering_fields(volume, position)
        if volume.identity in seen_identities:
            raise DuplicateVolumeIdentityError(volume.identity)
        seen_identities.add(volume.identity)

    return tuple(sorted(ordered_input, key=_ordering_key))
