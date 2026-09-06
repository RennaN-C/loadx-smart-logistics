from collections.abc import Sequence
from decimal import Decimal
from typing import NoReturn
from uuid import UUID

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    OrderItemInput,
    VolumeIdentity,
)


class VolumeDomainError(ValueError):
    code: str


class InvalidVolumeInputError(VolumeDomainError):
    code = "INVALID_VOLUME_INPUT"

    def __init__(
        self,
        field_name: str,
        reason: str,
        order_item_id: UUID | None = None,
    ) -> None:
        self.field_name = field_name
        self.reason = reason
        self.order_item_id = order_item_id
        super().__init__(f"{field_name} {reason}")


class DuplicateOrderItemError(VolumeDomainError):
    code = "DUPLICATE_ORDER_ITEM_ID"

    def __init__(self, order_item_id: UUID) -> None:
        self.order_item_id = order_item_id
        super().__init__(f"order_item_id {order_item_id} appears more than once")


def _raise_invalid(
    field_name: str,
    reason: str,
    order_item_id: UUID | None = None,
) -> NoReturn:
    raise InvalidVolumeInputError(field_name, reason, order_item_id)


def _validate_positive_int(
    value: object,
    field_name: str,
    order_item_id: UUID | None = None,
) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        _raise_invalid(field_name, "must be a positive integer", order_item_id)


def calculate_volume_cm3(width_cm: int, height_cm: int, length_cm: int) -> int:
    _validate_positive_int(width_cm, "width_cm")
    _validate_positive_int(height_cm, "height_cm")
    _validate_positive_int(length_cm, "length_cm")
    return width_cm * height_cm * length_cm


def _validate_order_item(item: OrderItemInput) -> None:
    identity = item.order_item_id if isinstance(item.order_item_id, UUID) else None

    for field_name in ("order_id", "order_item_id", "product_id"):
        if not isinstance(getattr(item, field_name), UUID):
            _raise_invalid(field_name, "must be a UUID", identity)

    _validate_positive_int(item.quantity, "quantity", identity)
    _validate_positive_int(item.delivery_sequence, "delivery_sequence", identity)
    _validate_positive_int(item.width_cm, "width_cm", identity)
    _validate_positive_int(item.height_cm, "height_cm", identity)
    _validate_positive_int(item.length_cm, "length_cm", identity)

    if not isinstance(item.weight_kg, Decimal):
        _raise_invalid("weight_kg", "must be a Decimal", identity)
    if not item.weight_kg.is_finite() or item.weight_kg <= 0:
        _raise_invalid("weight_kg", "must be a positive finite Decimal", identity)

    for field_name in ("fragile", "stackable", "rotation_allowed"):
        if not isinstance(getattr(item, field_name), bool):
            _raise_invalid(field_name, "must be a boolean", identity)

    if item.product_name is not None and not isinstance(item.product_name, str):
        _raise_invalid("product_name", "must be a string or None", identity)


def expand_order_items(
    items: Sequence[OrderItemInput],
) -> tuple[IndividualVolume, ...]:
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
        _raise_invalid("items", "must be an ordered sequence of OrderItemInput")

    expanded_volumes: list[IndividualVolume] = []
    seen_order_item_ids: set[UUID] = set()

    for position, item in enumerate(tuple(items)):
        if not isinstance(item, OrderItemInput):
            _raise_invalid(
                f"items[{position}]",
                "must be an OrderItemInput",
            )
        _validate_order_item(item)
        if item.order_item_id in seen_order_item_ids:
            raise DuplicateOrderItemError(item.order_item_id)
        seen_order_item_ids.add(item.order_item_id)

        volume_cm3 = item.width_cm * item.height_cm * item.length_cm
        for offset in range(item.quantity):
            expanded_volumes.append(
                IndividualVolume(
                    identity=VolumeIdentity(
                        order_item_id=item.order_item_id,
                        volume_index=offset + 1,
                    ),
                    order_id=item.order_id,
                    product_id=item.product_id,
                    product_name=item.product_name,
                    delivery_sequence=item.delivery_sequence,
                    original_width_cm=item.width_cm,
                    original_height_cm=item.height_cm,
                    original_length_cm=item.length_cm,
                    volume_cm3=volume_cm3,
                    weight_kg=item.weight_kg,
                    fragile=item.fragile,
                    stackable=item.stackable,
                    rotation_allowed=item.rotation_allowed,
                )
            )

    return tuple(expanded_volumes)
