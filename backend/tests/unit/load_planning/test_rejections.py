import pytest

from app.modules.load_planning.optimizer.placement import (
    NoValidPositionError,
    TruckDimensionsExceededError,
)
from app.modules.load_planning.optimizer.rejections import (
    REJECTION_REASON_PRECEDENCE,
    InvalidRejectionInputError,
    RejectionReason,
    select_rejection_reason,
)

APPROVED_REASON_VALUES = (
    "TRUCK_DIMENSIONS_EXCEEDED",
    "TRUCK_WEIGHT_EXCEEDED",
    "NON_STACKABLE_SUPPORT",
    "FRAGILE_SUPPORT_WEIGHT_EXCEEDED",
    "INSUFFICIENT_SUPPORT",
    "COLLISION",
    "NO_VALID_POSITION",
)


def test_rejection_catalog_matches_the_approved_precedence() -> None:
    assert tuple(reason.value for reason in RejectionReason) == APPROVED_REASON_VALUES
    assert (
        tuple(reason.value for reason in REJECTION_REASON_PRECEDENCE)
        == APPROVED_REASON_VALUES
    )


def test_placement_errors_use_catalog_codes() -> None:
    assert (
        TruckDimensionsExceededError.code
        == RejectionReason.TRUCK_DIMENSIONS_EXCEEDED.value
    )
    assert NoValidPositionError.code == RejectionReason.NO_VALID_POSITION.value


@pytest.mark.parametrize("reason", REJECTION_REASON_PRECEDENCE)
def test_select_rejection_reason_accepts_each_catalog_reason(
    reason: RejectionReason,
) -> None:
    assert select_rejection_reason((reason,)) is reason


def test_select_rejection_reason_obeys_every_precedence_pair() -> None:
    for higher_rank, higher_priority in enumerate(REJECTION_REASON_PRECEDENCE):
        for lower_priority in REJECTION_REASON_PRECEDENCE[higher_rank + 1 :]:
            assert (
                select_rejection_reason((lower_priority, higher_priority))
                is higher_priority
            )


def test_select_rejection_reason_is_independent_of_input_order() -> None:
    expected = RejectionReason.TRUCK_DIMENSIONS_EXCEEDED

    assert select_rejection_reason(REJECTION_REASON_PRECEDENCE) is expected
    assert select_rejection_reason(REJECTION_REASON_PRECEDENCE[::-1]) is expected


def test_select_rejection_reason_accepts_duplicates_without_mutating_input() -> None:
    reasons = [
        RejectionReason.COLLISION,
        RejectionReason.INSUFFICIENT_SUPPORT,
        RejectionReason.COLLISION,
    ]
    original = list(reasons)

    result = select_rejection_reason(reasons)

    assert result is RejectionReason.INSUFFICIENT_SUPPORT
    assert reasons == original


@pytest.mark.parametrize(
    "invalid_reasons", [(), "COLLISION", {RejectionReason.COLLISION}]
)
def test_select_rejection_reason_requires_a_non_empty_ordered_sequence(
    invalid_reasons: object,
) -> None:
    with pytest.raises(InvalidRejectionInputError) as exc_info:
        select_rejection_reason(invalid_reasons)  # type: ignore[arg-type]

    assert exc_info.value.code == "INVALID_REJECTION_INPUT"
    assert exc_info.value.field_name == "reasons"
    assert exc_info.value.code not in APPROVED_REASON_VALUES


@pytest.mark.parametrize("invalid_reason", ["COLLISION", None, 1])
def test_select_rejection_reason_rejects_values_outside_the_catalog(
    invalid_reason: object,
) -> None:
    with pytest.raises(InvalidRejectionInputError) as exc_info:
        select_rejection_reason([invalid_reason])  # type: ignore[list-item]

    assert exc_info.value.code == "INVALID_REJECTION_INPUT"
    assert exc_info.value.field_name == "reasons[0]"
