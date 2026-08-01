from dataclasses import dataclass
from decimal import Decimal
from enum import IntEnum
from uuid import UUID


class VolumeIndexBase(IntEnum):
    """Supported index policies while the persistence convention is pending."""

    ZERO = 0
    ONE = 1


@dataclass(frozen=True)
class OrderItemInput:
    order_id: UUID
    order_item_id: UUID
    product_id: UUID
    quantity: int
    delivery_sequence: int
    width_cm: int
    height_cm: int
    length_cm: int
    weight_kg: Decimal
    fragile: bool
    stackable: bool
    rotation_allowed: bool
    product_name: str | None = None


@dataclass(frozen=True)
class VolumeIdentity:
    order_item_id: UUID
    volume_index: int


@dataclass(frozen=True)
class IndividualVolume:
    identity: VolumeIdentity
    order_id: UUID
    product_id: UUID
    product_name: str | None
    delivery_sequence: int
    original_width_cm: int
    original_height_cm: int
    original_length_cm: int
    volume_cm3: int
    weight_kg: Decimal
    fragile: bool
    stackable: bool
    rotation_allowed: bool

    @property
    def order_item_id(self) -> UUID:
        return self.identity.order_item_id

    @property
    def volume_index(self) -> int:
        return self.identity.volume_index
