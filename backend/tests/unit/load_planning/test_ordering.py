from decimal import Decimal
from itertools import permutations
from uuid import UUID

import pytest

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.ordering import (
    DuplicateVolumeIdentityError,
    InvalidVolumeOrderingInputError,
    order_volumes,
)


def make_volume(identity_number: int, **overrides: object) -> IndividualVolume:
    values: dict[str, object] = {
        "identity": VolumeIdentity(
            order_item_id=UUID(int=identity_number),
            volume_index=1,
        ),
        "order_id": UUID(int=100 + identity_number),
        "product_id": UUID(int=200 + identity_number),
        "product_name": f"Volume {identity_number}",
        "delivery_sequence": 1,
        "original_width_cm": 10,
        "original_height_cm": 10,
        "original_length_cm": 10,
        "volume_cm3": 1_000,
        "weight_kg": Decimal("10.000"),
        "fragile": False,
        "stackable": True,
        "rotation_allowed": True,
    }
    values.update(overrides)
    return IndividualVolume(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("preferred_overrides", "other_overrides"),
    [
        ({"volume_cm3": 1_001}, {"volume_cm3": 1_000}),
        ({"weight_kg": Decimal("10.001")}, {"weight_kg": Decimal("10.000")}),
        ({"stackable": False}, {"stackable": True}),
        ({"fragile": False}, {"fragile": True}),
        ({"delivery_sequence": 2}, {"delivery_sequence": 1}),
    ],
)
def test_order_volumes_applies_each_business_criterion_before_identity(
    preferred_overrides: dict[str, object],
    other_overrides: dict[str, object],
) -> None:
    preferred = make_volume(2, **preferred_overrides)
    other = make_volume(1, **other_overrides)

    assert order_volumes([other, preferred]) == (preferred, other)


def test_order_volumes_applies_criteria_in_the_approved_precedence() -> None:
    largest = make_volume(
        7,
        volume_cm3=2_000,
        weight_kg=Decimal("1.000"),
        stackable=True,
        fragile=True,
        delivery_sequence=1,
    )
    heaviest = make_volume(
        6,
        weight_kg=Decimal("20.000"),
        stackable=True,
        fragile=True,
        delivery_sequence=1,
    )
    non_stackable = make_volume(
        5,
        stackable=False,
        fragile=True,
        delivery_sequence=1,
    )
    non_fragile_later_delivery = make_volume(4, delivery_sequence=2)
    non_fragile_earlier_delivery = make_volume(3, delivery_sequence=1)
    fragile = make_volume(2, fragile=True, delivery_sequence=9)

    result = order_volumes(
        [
            fragile,
            non_fragile_earlier_delivery,
            non_stackable,
            largest,
            non_fragile_later_delivery,
            heaviest,
        ]
    )

    assert result == (
        largest,
        heaviest,
        non_stackable,
        non_fragile_later_delivery,
        non_fragile_earlier_delivery,
        fragile,
    )


def test_order_volumes_uses_identity_as_the_final_tie_breaker() -> None:
    later_item = make_volume(2)
    later_index = make_volume(
        1,
        identity=VolumeIdentity(order_item_id=UUID(int=1), volume_index=2),
    )
    first_identity = make_volume(
        1,
        identity=VolumeIdentity(order_item_id=UUID(int=1), volume_index=1),
    )

    assert order_volumes([later_item, later_index, first_identity]) == (
        first_identity,
        later_index,
        later_item,
    )


def test_order_volumes_is_independent_from_input_order() -> None:
    volumes = [
        make_volume(1, volume_cm3=500),
        make_volume(2, weight_kg=Decimal("12.000")),
        make_volume(3, stackable=False),
        make_volume(4, fragile=True),
    ]
    expected = order_volumes(volumes)

    for permutation in permutations(volumes):
        assert order_volumes(permutation) == expected


def test_order_volumes_does_not_mutate_the_input_and_returns_a_tuple() -> None:
    volumes = [make_volume(2), make_volume(1)]
    original = list(volumes)

    result = order_volumes(volumes)

    assert volumes == original
    assert isinstance(result, tuple)
    assert result == (volumes[1], volumes[0])


def test_order_volumes_accepts_an_empty_sequence() -> None:
    assert order_volumes([]) == ()


def test_order_volumes_rejects_an_unordered_collection() -> None:
    with pytest.raises(InvalidVolumeOrderingInputError) as exc_info:
        order_volumes({make_volume(1)})  # type: ignore[arg-type]

    assert exc_info.value.code == "INVALID_VOLUME_ORDERING_INPUT"
    assert exc_info.value.field_name == "volumes"


def test_order_volumes_rejects_an_invalid_sequence_element() -> None:
    with pytest.raises(InvalidVolumeOrderingInputError) as exc_info:
        order_volumes([object()])  # type: ignore[list-item]

    assert exc_info.value.field_name == "volumes[0]"


def test_order_volumes_rejects_duplicate_identity() -> None:
    volume = make_volume(1)
    duplicate = make_volume(1, product_id=UUID(int=999))

    for input_order in ([volume, duplicate], [duplicate, volume]):
        with pytest.raises(DuplicateVolumeIdentityError) as exc_info:
            order_volumes(input_order)

        assert exc_info.value.code == "DUPLICATE_VOLUME_IDENTITY"
        assert exc_info.value.identity == volume.identity


@pytest.mark.parametrize(
    ("overrides", "field_name"),
    [
        ({"identity": object()}, "volumes[0].identity"),
        (
            {
                "identity": VolumeIdentity(
                    order_item_id="not-a-uuid",  # type: ignore[arg-type]
                    volume_index=1,
                )
            },
            "volumes[0].order_item_id",
        ),
        (
            {"identity": VolumeIdentity(order_item_id=UUID(int=1), volume_index=0)},
            "volumes[0].volume_index",
        ),
        ({"volume_cm3": True}, "volumes[0].volume_cm3"),
        ({"delivery_sequence": 0}, "volumes[0].delivery_sequence"),
        ({"weight_kg": 10}, "volumes[0].weight_kg"),
        ({"weight_kg": Decimal("NaN")}, "volumes[0].weight_kg"),
        ({"weight_kg": Decimal(0)}, "volumes[0].weight_kg"),
        ({"stackable": 1}, "volumes[0].stackable"),
        ({"fragile": 0}, "volumes[0].fragile"),
    ],
)
def test_order_volumes_rejects_invalid_ordering_fields(
    overrides: dict[str, object],
    field_name: str,
) -> None:
    volume = make_volume(1, **overrides)

    with pytest.raises(InvalidVolumeOrderingInputError) as exc_info:
        order_volumes([volume])

    assert exc_info.value.code == "INVALID_VOLUME_ORDERING_INPUT"
    assert exc_info.value.field_name == field_name
