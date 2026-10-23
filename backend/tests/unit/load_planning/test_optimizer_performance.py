"""Work-count regressions and differential physical checks, without timing gates."""

import pytest

from app.modules.load_planning.optimizer import multi_truck, support
from app.modules.load_planning.optimizer.geometry import is_collision_free
from app.modules.load_planning.optimizer.rejections import (
    REJECTION_REASON_PRECEDENCE,
    RejectionReason,
)
from tests.unit.load_planning.test_support import make_candidate
from tests.unit.test_multi_truck_optimizer import make_candidate as make_truck
from tests.unit.test_multi_truck_optimizer import make_volume


def full_support_reasons(placements):
    by_id = {p.identity: p for p in placements}
    reasons = set()
    for assessment in support.analyze_support_configuration(placements):
        if not assessment.is_fully_supported:
            reasons.add(RejectionReason.INSUFFICIENT_SUPPORT)
        if any(
            not by_id[i].volume.stackable
            for i in assessment.direct_supporter_identities
        ):
            reasons.add(RejectionReason.NON_STACKABLE_SUPPORT)
        if any(
            by_id[i].volume.fragile
            for i in assessment.load_bearing_supporter_identities
        ):
            reasons.add(RejectionReason.FRAGILE_SUPPORT_WEIGHT_EXCEEDED)
    return tuple(r for r in REJECTION_REASON_PRECEDENCE if r in reasons)


@pytest.mark.parametrize(
    "fragile,stackable", [(False, True), (True, True), (False, False)]
)
def test_rejection_fast_path_matches_complete_physical_analysis(fragile, stackable):
    from app.modules.load_planning.optimizer.engine import _support_rejection_reasons

    placed = (
        make_candidate(1, fragile=fragile, stackable=stackable),
        make_candidate(2, position_x_cm=10),
    )
    assert support.is_support_configuration_valid(placed)
    for x in (0, 5, 10, 15, 20):
        for y in (0, 10, 20):
            for z in (0, 5, 10):
                candidate = make_candidate(
                    3, position_x_cm=x, position_y_cm=y, position_z_cm=z
                )
                if not is_collision_free(candidate.box, tuple(p.box for p in placed)):
                    continue
                assert _support_rejection_reasons(
                    candidate, placed
                ) == full_support_reasons((*placed, candidate))


def test_support_index_checks_only_contacts_at_the_matching_height(monkeypatch):
    placements = tuple(make_candidate(i + 1, position_y_cm=i * 10) for i in range(20))
    contact = support._contact_rectangle
    calls = 0

    def track(upper, lower):
        nonlocal calls
        calls += 1
        return contact(upper, lower)

    monkeypatch.setattr(support, "_contact_rectangle", track)
    assessments = support.analyze_support_configuration(placements)
    assert all(row.is_fully_supported for row in assessments)
    assert len(assessments[-1].load_bearing_supporter_identities) == 19
    assert calls == 19


def test_identical_trucks_reuse_packing_without_reassigning_volume_identity(
    monkeypatch,
):
    calculate = multi_truck.calculate_volume_load_plan
    calls = 0

    def track(capacity, volumes):
        nonlocal calls
        calls += 1
        return calculate(capacity, volumes)

    monkeypatch.setattr(multi_truck, "calculate_volume_load_plan", track)
    trucks = tuple(make_truck(i, width_cm=30) for i in range(1, 11))
    volumes = tuple(make_volume(i) for i in (1, 2, 3))
    result = multi_truck.optimize_multi_truck(trucks, volumes)
    assert result.complete
    assert result.parts[0].truck_id == trucks[0].truck_id
    assert result.parts[0].volumes == volumes
    assert calls == result.attempt_count == 1


def test_different_truck_capacities_are_not_shared(monkeypatch):
    calculate = multi_truck.calculate_volume_load_plan
    capacities = []

    def track(capacity, volumes):
        capacities.append(capacity)
        return calculate(capacity, volumes)

    monkeypatch.setattr(multi_truck, "calculate_volume_load_plan", track)
    trucks = (make_truck(1, width_cm=20), make_truck(2, width_cm=30))
    result = multi_truck.optimize_multi_truck(
        trucks, tuple(make_volume(i) for i in (1, 2, 3))
    )
    assert result.complete
    assert result.parts[0].truck_id == trucks[1].truck_id
    assert len(capacities) == 2
