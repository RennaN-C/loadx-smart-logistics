import uuid
from decimal import Decimal

import pytest

from app.modules.load_planning.optimizer.capacity import TruckCapacityInput
from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)
from app.modules.load_planning.optimizer.engine import calculate_volume_load_plan
from app.modules.load_planning.optimizer.multi_truck import (
    MultiTruckCandidate,
    optimize_multi_truck,
)

ORDER_ID = uuid.UUID(int=10)
PRODUCT_ID = uuid.UUID(int=20)
ITEM_ID = uuid.UUID(int=30)


def make_volume(
    index: int,
    *,
    size_cm: int = 10,
    weight_kg: str = "1.000",
) -> IndividualVolume:
    return IndividualVolume(
        identity=VolumeIdentity(
            order_item_id=ITEM_ID,
            volume_index=index,
        ),
        order_id=ORDER_ID,
        product_id=PRODUCT_ID,
        product_name="Caixa",
        delivery_sequence=1,
        original_width_cm=size_cm,
        original_height_cm=size_cm,
        original_length_cm=size_cm,
        volume_cm3=size_cm**3,
        weight_kg=Decimal(weight_kg),
        fragile=False,
        stackable=True,
        rotation_allowed=True,
    )


def make_candidate(
    identifier: int,
    *,
    width_cm: int,
    height_cm: int = 10,
    length_cm: int = 10,
    max_weight_kg: str = "100.00",
) -> MultiTruckCandidate:
    return MultiTruckCandidate(
        truck_id=uuid.UUID(int=identifier),
        capacity=TruckCapacityInput(
            internal_width_cm=width_cm,
            internal_height_cm=height_cm,
            internal_length_cm=length_cm,
            max_weight_kg=Decimal(max_weight_kg),
        ),
    )


@pytest.mark.parametrize(
    ("truck_width_cm", "expected_trucks"),
    [
        (30, 1),
        (20, 2),
        (10, 3),
    ],
)
def test_optimizer_uses_minimum_level_needed_for_complete_load(
    truck_width_cm: int,
    expected_trucks: int,
) -> None:
    candidates = tuple(
        make_candidate(identifier, width_cm=truck_width_cm) for identifier in (1, 2, 3)
    )
    volumes = tuple(make_volume(index) for index in (1, 2, 3))

    result = optimize_multi_truck(candidates, volumes)

    assert result.complete
    assert len(result.parts) == expected_trucks
    assert not result.remaining_volumes
    assert {volume.identity for part in result.parts for volume in part.volumes} == {
        volume.identity for volume in volumes
    }
    assert all(
        not part.load_plan.rejected_volumes or expected_trucks > 1
        for part in result.parts
    )


def test_maximum_load_can_span_ten_trucks_without_losing_volume_identity() -> None:
    candidates = tuple(
        make_candidate(identifier, width_cm=100, length_cm=20)
        for identifier in range(1, 11)
    )
    volumes = tuple(make_volume(index) for index in range(1, 201))
    result = optimize_multi_truck(candidates, volumes)
    assert result.complete
    assert len(result.parts) == 10
    placed = [volume.identity for part in result.parts for volume in part.volumes]
    assert len(placed) == len(set(placed)) == 200
    assert set(placed) == {volume.identity for volume in volumes}
    assert all(part.load_plan.metrics.loaded_count == 20 for part in result.parts)
    repeated = optimize_multi_truck(
        tuple(reversed(candidates)), tuple(reversed(volumes))
    )
    assert repeated == result


def test_optimizer_prefers_smaller_complete_single_truck() -> None:
    candidates = (
        make_candidate(2, width_cm=40),
        make_candidate(1, width_cm=30),
    )
    volumes = tuple(make_volume(index) for index in (1, 2, 3))

    result = optimize_multi_truck(candidates, volumes)

    assert result.complete
    assert len(result.parts) == 1
    assert result.parts[0].truck_id == uuid.UUID(int=1)


def test_optimizer_uses_uuid_as_final_equivalent_truck_tie_breaker() -> None:
    candidates = (
        make_candidate(2, width_cm=30),
        make_candidate(1, width_cm=30),
    )
    volumes = tuple(make_volume(index) for index in (1, 2, 3))

    result = optimize_multi_truck(candidates, volumes)

    assert result.complete
    assert result.parts[0].truck_id == uuid.UUID(int=1)


def test_optimizer_is_independent_from_candidate_and_volume_input_order() -> None:
    candidates = (
        make_candidate(2, width_cm=10),
        make_candidate(1, width_cm=10),
    )
    volumes = (
        make_volume(2),
        make_volume(1),
    )

    first = optimize_multi_truck(candidates, volumes)
    second = optimize_multi_truck(
        tuple(reversed(candidates)),
        tuple(reversed(volumes)),
    )

    def signature(result):
        return tuple(
            sorted(
                (
                    part.truck_id,
                    tuple(
                        sorted(
                            (
                                volume.order_item_id,
                                volume.volume_index,
                            )
                            for volume in part.volumes
                        )
                    ),
                )
                for part in result.parts
            )
        )

    assert first.complete and second.complete
    assert signature(first) == signature(second)


@pytest.mark.parametrize(
    ("volume", "candidate", "expected_reason"),
    [
        (
            make_volume(1, weight_kg="5.000"),
            make_candidate(1, width_cm=30, max_weight_kg="4.00"),
            "TRUCK_WEIGHT_EXCEEDED",
        ),
        (
            make_volume(1, size_cm=20),
            make_candidate(
                1,
                width_cm=10,
                height_cm=10,
                length_cm=10,
            ),
            "TRUCK_DIMENSIONS_EXCEEDED",
        ),
    ],
)
def test_optimizer_explains_intrinsic_capacity_rejection(
    volume: IndividualVolume,
    candidate: MultiTruckCandidate,
    expected_reason: str,
) -> None:
    result = optimize_multi_truck((candidate,), (volume,))

    assert not result.complete
    assert result.parts == ()
    assert result.remaining_volumes == (volume,)
    assert result.failures[0].identity == volume.identity
    assert expected_reason in result.failures[0].reasons


def test_optimizer_returns_explainable_incomplete_result_for_insufficient_fleet() -> (
    None
):
    candidates = (
        make_candidate(1, width_cm=10),
        make_candidate(2, width_cm=10),
    )
    volumes = tuple(make_volume(index) for index in (1, 2, 3))

    result = optimize_multi_truck(candidates, volumes)

    assert not result.complete
    assert len(result.parts) == 2
    assert len(result.remaining_volumes) == 1
    assert result.failures
    assert result.attempt_count > 0


def test_optimizer_reuses_existing_single_truck_engine_without_changing_result() -> (
    None
):
    candidate = make_candidate(1, width_cm=30)
    volumes = tuple(make_volume(index) for index in (3, 1, 2))

    expected = calculate_volume_load_plan(
        candidate.capacity,
        volumes,
    )
    result = optimize_multi_truck((candidate,), volumes)

    assert result.complete
    assert len(result.parts) == 1
    assert result.parts[0].load_plan == expected
