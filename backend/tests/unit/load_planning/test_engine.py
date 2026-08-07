from dataclasses import FrozenInstanceError
from decimal import Decimal, Inexact, Rounded, localcontext
from typing import Never
from uuid import UUID

import pytest

import app.modules.load_planning.optimizer.engine as engine_module
from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import OrderItemInput
from app.modules.load_planning.optimizer.engine import (
    MAX_VOLUMES,
    EngineInvariantError,
    InvalidEngineInputError,
    LoadPlanResult,
    LoadPlanVolumeLimitExceededError,
    calculate_load_plan,
)
from app.modules.load_planning.optimizer.loading_sequence import (
    calculate_door_distance_cm,
)
from app.modules.load_planning.optimizer.rejections import RejectionReason
from app.modules.load_planning.optimizer.volumes import InvalidVolumeInputError


def make_truck(**overrides: object) -> TruckCapacityInput:
    values: dict[str, object] = {
        "internal_width_cm": 20,
        "internal_height_cm": 10,
        "internal_length_cm": 10,
        "max_weight_kg": Decimal("100.00"),
    }
    values.update(overrides)
    return TruckCapacityInput(**values)  # type: ignore[arg-type]


def make_item(identity_number: int, **overrides: object) -> OrderItemInput:
    values: dict[str, object] = {
        "order_id": UUID(int=100 + identity_number),
        "order_item_id": UUID(int=identity_number),
        "product_id": UUID(int=200 + identity_number),
        "product_name": f"Caixa {identity_number}",
        "quantity": 1,
        "delivery_sequence": 1,
        "width_cm": 10,
        "height_cm": 10,
        "length_cm": 10,
        "weight_kg": Decimal("1.000"),
        "fragile": False,
        "stackable": True,
        "rotation_allowed": False,
    }
    values.update(overrides)
    return OrderItemInput(**values)  # type: ignore[arg-type]


def rejection_reasons(result: LoadPlanResult) -> tuple[RejectionReason, ...]:
    return tuple(item.rejection_reason for item in result.rejected_volumes)


def test_engine_rejects_an_empty_order_item_sequence() -> None:
    with pytest.raises(InvalidEngineInputError) as exc_info:
        calculate_load_plan(make_truck(), [])

    assert exc_info.value.code == "INVALID_ENGINE_INPUT"
    assert exc_info.value.field_name == "order_items"
    assert "empty" in exc_info.value.reason


def test_engine_places_an_exact_fit_and_exposes_final_properties() -> None:
    result = calculate_load_plan(
        make_truck(
            internal_width_cm=10,
            internal_height_cm=10,
            internal_length_cm=10,
        ),
        [make_item(1)],
    )

    placed = result.placed_volumes[0]
    assert placed.identity.order_item_id == UUID(int=1)
    assert placed.position_x_cm == 0
    assert placed.position_y_cm == 0
    assert placed.position_z_cm == 0
    assert placed.used_width_cm == 10
    assert placed.used_height_cm == 10
    assert placed.used_length_cm == 10
    assert placed.rotation_code.value == "XYZ"
    assert placed.loading_sequence == 1
    assert result.metrics.occupancy_percent == Decimal("100.00")


def test_dimension_rejection_precedes_weight_rejection() -> None:
    result = calculate_load_plan(
        make_truck(
            internal_width_cm=10,
            max_weight_kg=Decimal("1.00"),
        ),
        [
            make_item(
                1,
                width_cm=20,
                weight_kg=Decimal("2.000"),
            )
        ],
    )

    assert rejection_reasons(result) == (RejectionReason.TRUCK_DIMENSIONS_EXCEEDED,)


def test_weight_rejection_does_not_change_total_for_the_next_volume() -> None:
    result = calculate_load_plan(
        make_truck(max_weight_kg=Decimal("1.00")),
        [
            make_item(1, weight_kg=Decimal("2.000")),
            make_item(2, weight_kg=Decimal("1.000")),
        ],
    )

    assert [item.identity.order_item_id for item in result.placed_volumes] == [
        UUID(int=2)
    ]
    assert rejection_reasons(result) == (RejectionReason.TRUCK_WEIGHT_EXCEEDED,)
    assert result.metrics.total_weight_kg == Decimal("1.000")


def test_collision_is_reported_when_no_collision_free_candidate_exists() -> None:
    result = calculate_load_plan(
        make_truck(
            internal_width_cm=10,
            internal_height_cm=10,
            internal_length_cm=10,
        ),
        [make_item(1, quantity=2)],
    )

    assert result.metrics.loaded_count == 1
    assert rejection_reasons(result) == (RejectionReason.COLLISION,)


@pytest.mark.parametrize(
    ("item_overrides", "expected_reason"),
    [
        (
            {"stackable": False},
            RejectionReason.NON_STACKABLE_SUPPORT,
        ),
        (
            {"fragile": True},
            RejectionReason.FRAGILE_SUPPORT_WEIGHT_EXCEEDED,
        ),
        (
            {"stackable": False, "fragile": True},
            RejectionReason.NON_STACKABLE_SUPPORT,
        ),
    ],
)
def test_engine_maps_structural_failures_with_catalog_precedence(
    item_overrides: dict[str, object],
    expected_reason: RejectionReason,
) -> None:
    result = calculate_load_plan(
        make_truck(
            internal_width_cm=10,
            internal_height_cm=20,
            internal_length_cm=10,
        ),
        [make_item(1, quantity=2, **item_overrides)],
    )

    assert result.metrics.loaded_count == 1
    assert rejection_reasons(result) == (expected_reason,)


def test_engine_reports_insufficient_support_at_the_furthest_frontier() -> None:
    truck = make_truck(
        internal_width_cm=10,
        internal_height_cm=20,
        internal_length_cm=10,
    )
    result = calculate_load_plan(
        truck,
        [
            make_item(1, width_cm=5, length_cm=5),
            make_item(2, width_cm=5, length_cm=5),
            make_item(3, width_cm=10, height_cm=1, length_cm=10),
        ],
    )

    assert result.metrics.loaded_count == 2
    assert rejection_reasons(result) == (RejectionReason.INSUFFICIENT_SUPPORT,)


def test_depth_only_block_uses_no_valid_position_not_incidental_collision() -> None:
    truck = make_truck(
        internal_width_cm=10,
        internal_height_cm=10,
        internal_length_cm=30,
    )
    result = calculate_load_plan(
        truck,
        [
            make_item(1, delivery_sequence=1, length_cm=20),
            make_item(2, delivery_sequence=2, length_cm=10),
        ],
    )

    assert [item.identity.order_item_id for item in result.placed_volumes] == [
        UUID(int=1)
    ]
    assert rejection_reasons(result) == (RejectionReason.NO_VALID_POSITION,)


def test_later_delivery_is_placed_deeper_and_loaded_first_on_the_floor() -> None:
    truck = make_truck(
        internal_width_cm=10,
        internal_height_cm=10,
        internal_length_cm=20,
    )
    result = calculate_load_plan(
        truck,
        [
            make_item(1, delivery_sequence=1),
            make_item(2, delivery_sequence=2),
        ],
    )
    bounds = engine_module.InternalDimensions(10, 10, 20)
    by_identity = {item.identity.order_item_id: item for item in result.placed_volumes}

    assert calculate_door_distance_cm(
        by_identity[UUID(int=2)].placement, bounds
    ) > calculate_door_distance_cm(by_identity[UUID(int=1)].placement, bounds)
    assert [item.identity.order_item_id for item in result.placed_volumes] == [
        UUID(int=2),
        UUID(int=1),
    ]


def test_support_topology_precedes_loading_priority() -> None:
    result = calculate_load_plan(
        make_truck(
            internal_width_cm=10,
            internal_height_cm=20,
            internal_length_cm=10,
        ),
        [make_item(1, quantity=2, delivery_sequence=9)],
    )

    assert [item.volume.volume_index for item in result.placed_volumes] == [1, 2]
    assert [item.loading_sequence for item in result.placed_volumes] == [1, 2]


def test_engine_is_independent_of_order_item_input_order() -> None:
    truck = make_truck(
        internal_width_cm=10,
        internal_height_cm=10,
        internal_length_cm=20,
    )
    first = make_item(1, delivery_sequence=1)
    second = make_item(2, delivery_sequence=2)

    assert calculate_load_plan(truck, [first, second]) == calculate_load_plan(
        truck,
        [second, first],
    )


def test_engine_is_independent_of_ambient_decimal_context() -> None:
    truck = make_truck(
        internal_width_cm=30,
        max_weight_kg=Decimal("0.60"),
    )
    items = [
        make_item(1, weight_kg=Decimal("0.100")),
        make_item(2, weight_kg=Decimal("0.200")),
        make_item(3, weight_kg=Decimal("0.300")),
    ]
    expected = calculate_load_plan(truck, items)

    with localcontext() as context:
        context.prec = 2
        context.traps[Inexact] = True
        context.traps[Rounded] = True
        actual = calculate_load_plan(truck, items)

    assert actual == expected
    assert actual.metrics.total_weight_kg == Decimal("0.600")


def test_engine_revalidates_the_complete_support_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        engine_module,
        "is_support_configuration_valid",
        lambda _placements: False,
    )

    with pytest.raises(EngineInvariantError) as exc_info:
        calculate_load_plan(make_truck(), [make_item(1)])

    assert exc_info.value.code == "LOAD_PLAN_INVARIANT_VIOLATION"
    assert exc_info.value.field_name == "placed_volumes"


def test_engine_rejects_more_than_the_approved_volume_limit() -> None:
    assert MAX_VOLUMES == 200

    with pytest.raises(LoadPlanVolumeLimitExceededError) as exc_info:
        calculate_load_plan(
            make_truck(),
            [make_item(1, quantity=201)],
        )

    assert exc_info.value.volume_count == 201
    assert exc_info.value.max_volumes == 200
    assert exc_info.value.code == "LOAD_PLAN_VOLUME_LIMIT_EXCEEDED"


def test_engine_accepts_exactly_the_approved_volume_limit() -> None:
    result = calculate_load_plan(
        make_truck(),
        [make_item(1, quantity=200, width_cm=21)],
    )

    assert result.metrics.loaded_count == 0
    assert result.metrics.unloaded_count == 200
    assert set(rejection_reasons(result)) == {RejectionReason.TRUCK_DIMENSIONS_EXCEEDED}


def test_volume_limit_is_checked_before_expansion_or_large_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_expansion_is_called(_items: object) -> Never:
        raise AssertionError("expansion must not run above the volume limit")

    monkeypatch.setattr(
        engine_module,
        "expand_order_items",
        fail_if_expansion_is_called,
    )

    with pytest.raises(LoadPlanVolumeLimitExceededError) as exc_info:
        calculate_load_plan(
            make_truck(),
            [make_item(1, quantity=10**100)],
        )

    assert exc_info.value.volume_count == 10**100


def test_engine_requires_the_pure_truck_contract() -> None:
    with pytest.raises(InvalidEngineInputError) as exc_info:
        calculate_load_plan(object(), [])  # type: ignore[arg-type]

    assert exc_info.value.code == "INVALID_ENGINE_INPUT"
    assert exc_info.value.field_name == "truck"


def test_engine_preserves_expansion_errors_for_other_volume_fields() -> None:
    with pytest.raises(InvalidVolumeInputError) as exc_info:
        calculate_load_plan(
            make_truck(),
            [make_item(1, width_cm=0)],
        )

    assert exc_info.value.field_name == "width_cm"


def test_engine_result_is_immutable() -> None:
    result = calculate_load_plan(make_truck(), [make_item(1)])

    with pytest.raises(FrozenInstanceError):
        result.metrics = result.metrics  # type: ignore[misc]
