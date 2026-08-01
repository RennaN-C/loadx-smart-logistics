from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.load_planning.optimizer.contracts import (
    OrderItemInput,
    VolumeIdentity,
    VolumeIndexBase,
)
from app.modules.load_planning.optimizer.volumes import (
    DuplicateOrderItemError,
    InvalidVolumeInputError,
    calculate_volume_cm3,
    expand_order_items,
)

ORDER_ID = UUID("00000000-0000-0000-0000-000000000001")
FIRST_ITEM_ID = UUID("00000000-0000-0000-0000-000000000002")
FIRST_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000003")
SECOND_ITEM_ID = UUID("00000000-0000-0000-0000-000000000004")
SECOND_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000005")


def make_order_item(**overrides: object) -> OrderItemInput:
    values: dict[str, object] = {
        "order_id": ORDER_ID,
        "order_item_id": FIRST_ITEM_ID,
        "product_id": FIRST_PRODUCT_ID,
        "product_name": "Caixa A",
        "quantity": 3,
        "delivery_sequence": 2,
        "width_cm": 60,
        "height_cm": 50,
        "length_cm": 40,
        "weight_kg": Decimal("12.500"),
        "fragile": True,
        "stackable": False,
        "rotation_allowed": True,
    }
    values.update(overrides)
    return OrderItemInput(**values)  # type: ignore[arg-type]


def test_calculate_volume_cm3_uses_integer_centimeters() -> None:
    assert calculate_volume_cm3(60, 50, 40) == 120_000


@pytest.mark.parametrize(
    ("width_cm", "height_cm", "length_cm", "field_name"),
    [
        (0, 50, 40, "width_cm"),
        (-1, 50, 40, "width_cm"),
        (60, 0, 40, "height_cm"),
        (60, -1, 40, "height_cm"),
        (60, 50, 0, "length_cm"),
        (60, 50, -1, "length_cm"),
    ],
)
def test_calculate_volume_cm3_rejects_non_positive_dimensions(
    width_cm: int,
    height_cm: int,
    length_cm: int,
    field_name: str,
) -> None:
    with pytest.raises(InvalidVolumeInputError) as exc_info:
        calculate_volume_cm3(width_cm, height_cm, length_cm)

    assert exc_info.value.code == "INVALID_VOLUME_INPUT"
    assert exc_info.value.field_name == field_name


@pytest.mark.parametrize(
    ("width_cm", "height_cm", "length_cm", "field_name"),
    [
        (True, 50, 40, "width_cm"),
        (60, 50.5, 40, "height_cm"),
        (60, 50, "40", "length_cm"),
    ],
)
def test_calculate_volume_cm3_requires_integer_dimensions(
    width_cm: object,
    height_cm: object,
    length_cm: object,
    field_name: str,
) -> None:
    with pytest.raises(InvalidVolumeInputError) as exc_info:
        calculate_volume_cm3(width_cm, height_cm, length_cm)  # type: ignore[arg-type]

    assert exc_info.value.field_name == field_name


def test_expand_order_items_materializes_every_unit_and_preserves_physical_data() -> (
    None
):
    order_item = make_order_item(quantity=3)

    volumes = expand_order_items([order_item], volume_index_base=VolumeIndexBase.ONE)

    assert len(volumes) == 3
    assert [volume.identity for volume in volumes] == [
        VolumeIdentity(order_item_id=FIRST_ITEM_ID, volume_index=1),
        VolumeIdentity(order_item_id=FIRST_ITEM_ID, volume_index=2),
        VolumeIdentity(order_item_id=FIRST_ITEM_ID, volume_index=3),
    ]
    for volume in volumes:
        assert volume.order_id == ORDER_ID
        assert volume.product_id == FIRST_PRODUCT_ID
        assert volume.product_name == "Caixa A"
        assert volume.delivery_sequence == 2
        assert (
            volume.original_width_cm,
            volume.original_height_cm,
            volume.original_length_cm,
        ) == (60, 50, 40)
        assert volume.volume_cm3 == 120_000
        assert volume.weight_kg == Decimal("12.500")
        assert volume.fragile is True
        assert volume.stackable is False
        assert volume.rotation_allowed is True


def test_expand_order_items_uses_an_explicit_zero_based_policy() -> None:
    volumes = expand_order_items(
        [make_order_item(quantity=2)],
        volume_index_base=VolumeIndexBase.ZERO,
    )

    assert [volume.identity.volume_index for volume in volumes] == [0, 1]


def test_expand_order_items_expands_multiple_items_in_input_order() -> None:
    first_item = make_order_item(quantity=2)
    second_item = make_order_item(
        order_item_id=SECOND_ITEM_ID,
        product_id=SECOND_PRODUCT_ID,
        product_name=None,
        quantity=1,
        width_cm=10,
        height_cm=20,
        length_cm=30,
    )
    items = [first_item, second_item]

    volumes = expand_order_items(items, volume_index_base=VolumeIndexBase.ONE)

    assert len(volumes) == 3
    assert [volume.identity for volume in volumes] == [
        VolumeIdentity(order_item_id=FIRST_ITEM_ID, volume_index=1),
        VolumeIdentity(order_item_id=FIRST_ITEM_ID, volume_index=2),
        VolumeIdentity(order_item_id=SECOND_ITEM_ID, volume_index=1),
    ]
    assert volumes[-1].volume_cm3 == 6_000
    assert items == [first_item, second_item]


def test_expand_order_items_is_deterministic() -> None:
    items = [make_order_item(quantity=2)]

    first_result = expand_order_items(items, volume_index_base=VolumeIndexBase.ONE)
    second_result = expand_order_items(items, volume_index_base=VolumeIndexBase.ONE)

    assert first_result == second_result


def test_expand_order_items_accepts_an_empty_sequence() -> None:
    assert expand_order_items([], volume_index_base=VolumeIndexBase.ONE) == ()


def test_expand_order_items_rejects_an_unordered_collection() -> None:
    with pytest.raises(InvalidVolumeInputError) as exc_info:
        expand_order_items(  # type: ignore[arg-type]
            {make_order_item()},
            volume_index_base=VolumeIndexBase.ONE,
        )

    assert exc_info.value.field_name == "items"


def test_expand_order_items_rejects_an_invalid_sequence_element() -> None:
    with pytest.raises(InvalidVolumeInputError) as exc_info:
        expand_order_items(  # type: ignore[list-item]
            [object()],
            volume_index_base=VolumeIndexBase.ONE,
        )

    assert exc_info.value.field_name == "items[0]"


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("quantity", 0),
        ("quantity", -1),
        ("delivery_sequence", 0),
        ("width_cm", 0),
        ("height_cm", -1),
        ("length_cm", 0),
        ("weight_kg", Decimal(0)),
        ("weight_kg", Decimal("-0.001")),
        ("weight_kg", Decimal("NaN")),
    ],
)
def test_expand_order_items_rejects_invalid_physical_input(
    field_name: str, invalid_value: object
) -> None:
    order_item = make_order_item(**{field_name: invalid_value})

    with pytest.raises(InvalidVolumeInputError) as exc_info:
        expand_order_items([order_item], volume_index_base=VolumeIndexBase.ONE)

    assert exc_info.value.code == "INVALID_VOLUME_INPUT"
    assert exc_info.value.field_name == field_name
    assert exc_info.value.order_item_id == FIRST_ITEM_ID


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("order_id", "not-a-uuid"),
        ("order_item_id", "not-a-uuid"),
        ("product_id", "not-a-uuid"),
        ("quantity", True),
        ("quantity", 1.5),
        ("delivery_sequence", True),
        ("width_cm", True),
        ("height_cm", 50.5),
        ("length_cm", "40"),
        ("weight_kg", "12.500"),
        ("weight_kg", Decimal("Infinity")),
        ("fragile", 0),
        ("stackable", "yes"),
        ("rotation_allowed", None),
        ("product_name", 123),
    ],
)
def test_expand_order_items_rejects_invalid_contract_types(
    field_name: str,
    invalid_value: object,
) -> None:
    order_item = make_order_item(**{field_name: invalid_value})

    with pytest.raises(InvalidVolumeInputError) as exc_info:
        expand_order_items([order_item], volume_index_base=VolumeIndexBase.ONE)

    assert exc_info.value.field_name == field_name


def test_expand_order_items_rejects_duplicate_order_item_identity() -> None:
    duplicate = make_order_item(product_id=SECOND_PRODUCT_ID)

    with pytest.raises(DuplicateOrderItemError) as exc_info:
        expand_order_items(
            [make_order_item(), duplicate],
            volume_index_base=VolumeIndexBase.ONE,
        )

    assert exc_info.value.code == "DUPLICATE_ORDER_ITEM_ID"
    assert exc_info.value.order_item_id == FIRST_ITEM_ID


def test_expand_order_items_requires_a_volume_index_policy() -> None:
    with pytest.raises(TypeError):
        expand_order_items([make_order_item()])  # type: ignore[call-arg]


def test_expand_order_items_rejects_an_untyped_volume_index_policy() -> None:
    with pytest.raises(InvalidVolumeInputError) as exc_info:
        expand_order_items([make_order_item()], volume_index_base=1)  # type: ignore[arg-type]

    assert exc_info.value.field_name == "volume_index_base"
