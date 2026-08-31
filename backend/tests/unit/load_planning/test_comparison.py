from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Never
from uuid import UUID

import pytest

from app.modules.load_planning.optimizer import comparison as comparison_module
from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.comparison import (
    MAX_COMPARISON_TRUCKS,
    MIN_COMPARISON_TRUCKS,
    InvalidTruckComparisonInputError,
    TruckComparisonCandidate,
    TruckComparisonLimitExceededError,
    compare_trucks,
)
from app.modules.load_planning.optimizer.contracts import OrderItemInput
from app.modules.load_planning.optimizer.engine import (
    LoadPlanVolumeLimitExceededError,
    calculate_load_plan,
)
from app.modules.load_planning.optimizer.geometry import (
    InternalDimensions,
    fits_within_bounds,
    is_collision_free,
)
from app.modules.load_planning.optimizer.rejections import RejectionReason
from app.modules.load_planning.optimizer.support import (
    is_support_configuration_valid,
)


def make_candidate(
    identity: int,
    **capacity_overrides: object,
) -> TruckComparisonCandidate:
    capacity_values: dict[str, object] = {
        "internal_width_cm": 20,
        "internal_height_cm": 10,
        "internal_length_cm": 10,
        "max_weight_kg": Decimal("10.00"),
    }
    capacity_values.update(capacity_overrides)
    return TruckComparisonCandidate(
        truck_id=UUID(int=identity),
        capacity=TruckCapacityInput(**capacity_values),  # type: ignore[arg-type]
    )


def make_item(
    identity: int = 1,
    **overrides: object,
) -> OrderItemInput:
    values: dict[str, object] = {
        "order_id": UUID(int=10_000 + identity),
        "order_item_id": UUID(int=20_000 + identity),
        "product_id": UUID(int=30_000 + identity),
        "quantity": 1,
        "delivery_sequence": 1,
        "width_cm": 10,
        "height_cm": 10,
        "length_cm": 10,
        "weight_kg": Decimal("1.000"),
        "fragile": False,
        "stackable": True,
        "rotation_allowed": True,
        "product_name": f"Product {identity}",
    }
    values.update(overrides)
    return OrderItemInput(**values)  # type: ignore[arg-type]


def test_comparison_accepts_ten_trucks_and_preserves_candidate_order() -> None:
    candidates = tuple(
        make_candidate(identity) for identity in range(MAX_COMPARISON_TRUCKS, 0, -1)
    )

    results = compare_trucks(candidates, (make_item(),))

    assert len(results) == MAX_COMPARISON_TRUCKS
    assert [result.truck_id for result in results] == [
        candidate.truck_id for candidate in candidates
    ]


def test_comparison_rejects_eleven_trucks_before_calling_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_engine_is_called(*_args: object, **_kwargs: object) -> Never:
        raise AssertionError("engine must not run above the truck limit")

    monkeypatch.setattr(
        comparison_module,
        "calculate_load_plan",
        fail_if_engine_is_called,
    )
    candidates = tuple(
        make_candidate(identity) for identity in range(1, MAX_COMPARISON_TRUCKS + 2)
    )

    with pytest.raises(TruckComparisonLimitExceededError) as exc_info:
        compare_trucks(candidates, (make_item(),))

    assert exc_info.value.truck_count == 11
    assert exc_info.value.max_trucks == MAX_COMPARISON_TRUCKS


@pytest.mark.parametrize("truck_count", [0, MIN_COMPARISON_TRUCKS - 1])
def test_comparison_rejects_fewer_than_two_trucks_before_calling_engine(
    truck_count: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_engine_is_called(*_args: object, **_kwargs: object) -> Never:
        raise AssertionError("engine must not run below the truck minimum")

    monkeypatch.setattr(
        comparison_module,
        "calculate_load_plan",
        fail_if_engine_is_called,
    )
    candidates = tuple(
        make_candidate(identity) for identity in range(1, truck_count + 1)
    )

    with pytest.raises(InvalidTruckComparisonInputError) as exc_info:
        compare_trucks(candidates, (make_item(),))

    assert exc_info.value.field_name == "candidates"
    assert exc_info.value.reason == "must contain at least 2 candidates"


def test_comparison_rejects_duplicate_truck_ids_before_calling_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_engine_is_called(*_args: object, **_kwargs: object) -> Never:
        raise AssertionError("engine must not run with duplicate truck ids")

    monkeypatch.setattr(
        comparison_module,
        "calculate_load_plan",
        fail_if_engine_is_called,
    )
    candidate = make_candidate(1)

    with pytest.raises(InvalidTruckComparisonInputError) as exc_info:
        compare_trucks((candidate, candidate), (make_item(),))

    assert exc_info.value.field_name == "candidates"
    assert exc_info.value.reason == "must not contain duplicate truck ids"


@pytest.mark.parametrize(
    "candidates",
    [
        {make_candidate(1)},
        (candidate for candidate in (make_candidate(1),)),
        "not-a-candidate-sequence",
    ],
)
def test_comparison_requires_an_ordered_candidate_sequence(
    candidates: object,
) -> None:
    with pytest.raises(InvalidTruckComparisonInputError) as exc_info:
        compare_trucks(candidates, (make_item(),))  # type: ignore[arg-type]

    assert exc_info.value.field_name == "candidates"


def test_comparison_validates_candidate_elements() -> None:
    with pytest.raises(InvalidTruckComparisonInputError) as exc_info:
        compare_trucks(  # type: ignore[arg-type]
            (object(), make_candidate(2)),
            (make_item(),),
        )

    assert exc_info.value.field_name == "candidates[0]"


@pytest.mark.parametrize(
    "order_items",
    [
        {make_item()},
        (item for item in (make_item(),)),
        "not-an-order-item-sequence",
    ],
)
def test_comparison_requires_an_ordered_order_item_sequence(
    order_items: object,
) -> None:
    with pytest.raises(InvalidTruckComparisonInputError) as exc_info:
        compare_trucks(
            (make_candidate(1), make_candidate(2)),
            order_items,  # type: ignore[arg-type]
        )

    assert exc_info.value.field_name == "order_items"


def test_comparison_validates_order_item_elements_and_quantity() -> None:
    with pytest.raises(InvalidTruckComparisonInputError) as element_error:
        compare_trucks(  # type: ignore[arg-type]
            (make_candidate(1), make_candidate(2)),
            (object(),),
        )
    with pytest.raises(InvalidTruckComparisonInputError) as quantity_error:
        compare_trucks(
            (make_candidate(1), make_candidate(2)),
            (make_item(quantity=True),),
        )

    assert element_error.value.field_name == "order_items[0]"
    assert quantity_error.value.field_name == "order_items[0].quantity"


def test_candidate_validates_uuid_and_pure_capacity_types() -> None:
    with pytest.raises(InvalidTruckComparisonInputError) as uuid_error:
        TruckComparisonCandidate(  # type: ignore[arg-type]
            truck_id="not-a-uuid",
            capacity=make_candidate(1).capacity,
        )
    with pytest.raises(InvalidTruckComparisonInputError) as capacity_error:
        TruckComparisonCandidate(  # type: ignore[arg-type]
            truck_id=UUID(int=1),
            capacity=object(),
        )

    assert uuid_error.value.field_name == "truck_id"
    assert capacity_error.value.field_name == "capacity"


def test_comparison_results_are_immutable() -> None:
    result = compare_trucks(
        (make_candidate(1), make_candidate(2)),
        (make_item(),),
    )[0]

    with pytest.raises(FrozenInstanceError):
        result.truck_id = UUID(int=2)  # type: ignore[misc]


def test_each_comparison_result_equals_a_direct_engine_execution() -> None:
    candidates = (
        make_candidate(2, internal_width_cm=20),
        make_candidate(1, internal_width_cm=10),
    )
    items = (make_item(1), make_item(2, delivery_sequence=2))

    results = compare_trucks(candidates, items)

    assert [result.load_plan for result in results] == [
        calculate_load_plan(candidate.capacity, items) for candidate in candidates
    ]


def test_comparison_is_deterministic() -> None:
    candidates = (
        make_candidate(1, internal_width_cm=10),
        make_candidate(2, internal_width_cm=20),
    )
    items = (make_item(2, delivery_sequence=2), make_item(1))

    assert compare_trucks(candidates, items) == compare_trucks(candidates, items)


def test_candidates_are_isolated_from_each_other() -> None:
    first = make_candidate(1, internal_width_cm=10)
    second = make_candidate(2, internal_width_cm=20)
    alternate = make_candidate(3, internal_width_cm=30)
    items = (make_item(1), make_item(2))

    combined = compare_trucks((first, second), items)
    first_with_alternate = compare_trucks((first, alternate), items)[0]
    second_with_alternate = compare_trucks((alternate, second), items)[1]

    assert combined[0] == first_with_alternate
    assert combined[1] == second_with_alternate
    assert combined[0].load_plan is not combined[1].load_plan


def test_comparison_does_not_mutate_candidate_or_workload_inputs() -> None:
    candidates = [make_candidate(2), make_candidate(1)]
    items = [make_item(2), make_item(1)]
    original_candidates = list(candidates)
    original_items = list(items)

    compare_trucks(candidates, items)

    assert candidates == original_candidates
    assert items == original_items


def test_comparison_preserves_rejections_weight_and_geometry() -> None:
    dimension_limited = make_candidate(
        1,
        internal_width_cm=5,
        internal_height_cm=5,
        internal_length_cm=5,
    )
    weight_limited = make_candidate(
        2,
        max_weight_kg=Decimal("1.500"),
    )
    fitting = make_candidate(3)
    items = (make_item(quantity=2),)

    dimension_result, weight_result, fitting_result = compare_trucks(
        (dimension_limited, weight_limited, fitting),
        items,
    )

    assert {
        rejected.rejection_reason
        for rejected in dimension_result.load_plan.rejected_volumes
    } == {RejectionReason.TRUCK_DIMENSIONS_EXCEEDED}
    assert {
        rejected.rejection_reason
        for rejected in weight_result.load_plan.rejected_volumes
    } == {RejectionReason.TRUCK_WEIGHT_EXCEEDED}

    for comparison_result in (
        dimension_result,
        weight_result,
        fitting_result,
    ):
        load_plan = comparison_result.load_plan
        assert load_plan.metrics.total_weight_kg <= load_plan.capacity.max_weight_kg
        assert all(
            isinstance(rejected.rejection_reason, RejectionReason)
            for rejected in load_plan.rejected_volumes
        )

        bounds = InternalDimensions(
            internal_width_cm=load_plan.capacity.internal_width_cm,
            internal_height_cm=load_plan.capacity.internal_height_cm,
            internal_length_cm=load_plan.capacity.internal_length_cm,
        )
        placements = tuple(
            sequenced.placement for sequenced in load_plan.placed_volumes
        )
        assert all(
            fits_within_bounds(placement.box, bounds) for placement in placements
        )
        assert all(
            is_collision_free(
                placement.box,
                tuple(other.box for other in placements[position + 1 :]),
            )
            for position, placement in enumerate(placements)
        )
        assert is_support_configuration_valid(placements)

    assert fitting_result.load_plan.metrics.loaded_count == 2
    assert fitting_result.load_plan.metrics.unloaded_count == 0


def test_comparison_propagates_the_engine_volume_limit() -> None:
    candidates = (make_candidate(1), make_candidate(2))

    accepted = compare_trucks(
        candidates,
        (make_item(quantity=200, width_cm=21),),
    )[0]
    assert accepted.load_plan.metrics.unloaded_count == 200

    with pytest.raises(LoadPlanVolumeLimitExceededError) as exc_info:
        compare_trucks(
            candidates,
            (make_item(quantity=201),),
        )

    assert exc_info.value.volume_count == 201
    assert exc_info.value.max_volumes == 200
