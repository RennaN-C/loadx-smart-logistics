"""Exact geometry, deterministic decisions and bounded work, without timing gates."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from itertools import combinations, product
from pathlib import Path

import pytest

from app.modules.load_planning.optimizer import (
    engine,
    geometry,
    loading_sequence,
    multi_truck,
)
from app.modules.load_planning.optimizer.geometry import (
    InternalDimensions,
    PositionedAABB,
)
from app.modules.load_planning.optimizer.volumes import expand_order_items
from benchmarks.benchmark_scalability import _physical_check, fingerprint
from benchmarks.scalability_cases import PROFILES, build_case
from tests.unit.load_planning.test_support import make_candidate


def test_spatial_index_matches_independent_integer_interval_oracle():
    bounds = InternalDimensions(19, 17, 23)
    boxes = tuple(
        PositionedAABB(x, y, z, 1 + i % 5, 1 + i % 3, 1 + i % 7)
        for i, (x, y, z) in enumerate(product((0, 3, 9), (0, 2, 8), (0, 5, 13)))
    )
    index = geometry._CollisionIndex(bounds)
    placed = []
    for candidate in reversed(boxes):
        independent = all(
            any(
                a + size_a <= b or b + size_b <= a
                for a, size_a, b, size_b in (
                    (
                        candidate.position_x_cm,
                        candidate.used_width_cm,
                        other.position_x_cm,
                        other.used_width_cm,
                    ),
                    (
                        candidate.position_y_cm,
                        candidate.used_height_cm,
                        other.position_y_cm,
                        other.used_height_cm,
                    ),
                    (
                        candidate.position_z_cm,
                        candidate.used_length_cm,
                        other.position_z_cm,
                        other.used_length_cm,
                    ),
                )
            )
            for other in placed
        )
        assert index.is_collision_free(candidate) == independent
        assert geometry.is_collision_free(candidate, placed) == independent
        index.add(candidate)
        placed.append(candidate)


def test_spatial_index_avoids_testing_unrelated_cells(monkeypatch):
    bounds = InternalDimensions(800, 800, 800)
    index = geometry._CollisionIndex(bounds)
    boxes = [PositionedAABB(i * 4, 0, 0, 2, 2, 2) for i in range(200)]
    for box in boxes:
        index.add(box)
    calls = 0
    original = geometry.classify_aabb_relation

    def classify(first, second):
        nonlocal calls
        calls += 1
        return original(first, second)

    monkeypatch.setattr(geometry, "classify_aabb_relation", classify)
    candidate = PositionedAABB(0, 700, 700, 800, 2, 2)
    assert index.is_collision_free(candidate)
    assert calls == 0
    assert geometry.is_collision_free(candidate, boxes)
    assert calls == 200
    assert len(index._cells) <= 8**3


def test_depth_group_extrema_match_pairwise_oracle_and_validate_inputs():
    bounds = InternalDimensions(100, 100, 100)
    for distances in product((0, 10, 20), repeat=3):
        for sequences in product((1, 2, 3), repeat=3):
            placements = tuple(
                replace(
                    make_candidate(i + 1, position_z_cm=z),
                    volume=replace(
                        make_candidate(i + 1).volume, delivery_sequence=sequence
                    ),
                )
                for i, (z, sequence) in enumerate(
                    zip(distances, sequences, strict=True)
                )
            )
            expected = all(
                first.volume.delivery_sequence == second.volume.delivery_sequence
                or (first.volume.delivery_sequence - second.volume.delivery_sequence)
                * (
                    (second.position_z_cm + second.used_length_cm)
                    - (first.position_z_cm + first.used_length_cm)
                )
                >= 0
                for first, second in combinations(placements, 2)
            )
            assert (
                loading_sequence.is_delivery_depth_configuration_valid(
                    placements, bounds
                )
                == expected
            )
    with pytest.raises(loading_sequence.InvalidLoadingSequenceInputError):
        loading_sequence.is_delivery_depth_configuration_valid(
            (placements[0], placements[0]), bounds
        )


def test_depth_checks_visit_each_placement_once(monkeypatch):
    placements = tuple(make_candidate(i + 1, position_x_cm=i * 10) for i in range(200))
    bounds = InternalDimensions(2000, 10, 10)
    original = loading_sequence._door_distance_cm
    calls = 0

    def distance(placement, dimensions):
        nonlocal calls
        calls += 1
        return original(placement, dimensions)

    monkeypatch.setattr(loading_sequence, "_door_distance_cm", distance)
    assert loading_sequence.is_delivery_depth_configuration_valid(placements, bounds)
    assert calls == len(placements)


@pytest.mark.parametrize("profile", PROFILES)
def test_profiles_preserve_physics_and_input_order_independence(profile):
    case = build_case(profile, 25, 1)
    result = engine.calculate_load_plan(case.trucks[0], case.items)
    assert result == engine.calculate_load_plan(
        case.trucks[0], tuple(reversed(case.items))
    )
    assert result == engine.calculate_load_plan(case.trucks[0], case.items)
    _physical_check(result, expand_order_items(case.items))


def test_indexes_are_local_to_each_concurrent_execution():
    case = build_case("heterogeneous", 25, 1)
    expected = engine.calculate_load_plan(case.trucks[0], case.items)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                lambda _: engine.calculate_load_plan(case.trucks[0], case.items),
                range(8),
            )
        )
    assert all(row == expected for row in results)


@pytest.mark.parametrize("count", [201, 500, 1000])
def test_public_limit_still_rejects_before_expansion(count, monkeypatch):
    case = build_case("dense", 1, 1)

    def forbidden(_):
        pytest.fail("limit must be enforced before materialization")

    monkeypatch.setattr(engine, "expand_order_items", forbidden)
    with pytest.raises(engine.LoadPlanVolumeLimitExceededError) as error:
        engine.calculate_load_plan(
            case.trucks[0], (replace(case.items[0], quantity=count),)
        )
    assert error.value.max_volumes == engine.MAX_VOLUMES == 200


def test_final_revalidation_still_detects_a_broken_collision_index(monkeypatch):
    case = build_case("dense", 2, 1)
    monkeypatch.setattr(
        geometry._CollisionIndex, "is_collision_free", lambda *args: True
    )
    with pytest.raises(engine.EngineInvariantError, match="collision free"):
        engine.calculate_load_plan(case.trucks[0], case.items)


def test_reference_snapshots_preserve_complete_heuristic_v1_results():
    path = Path(__file__).with_name("scalability_reference.json")
    references = json.loads(path.read_text())
    for row in references["cases"]:
        case = build_case(row["profile"], row["volumes"], 1)
        result = engine.calculate_load_plan(case.trucks[0], case.items)
        assert fingerprint(result) == row["fingerprint"], row


def test_multi_reference_preserves_trucks_assignments_and_cache_attempts():
    from uuid import UUID

    references = json.loads(
        Path(__file__).with_name("scalability_reference.json").read_text()
    )
    for row in references["multi_cases"]:
        case = build_case(row["profile"], row["volumes"], row["trucks"])
        trucks = tuple(
            multi_truck.MultiTruckCandidate(UUID(int=index + 1), capacity)
            for index, capacity in enumerate(case.trucks)
        )
        volumes = expand_order_items(case.items)
        result = multi_truck.optimize_multi_truck(trucks, volumes)
        assert fingerprint(result) == row["fingerprint"], row
        assert result == multi_truck.optimize_multi_truck(
            tuple(reversed(trucks)), tuple(reversed(volumes))
        )
