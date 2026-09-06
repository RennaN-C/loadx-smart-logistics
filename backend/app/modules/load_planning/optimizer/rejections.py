from collections.abc import Sequence
from enum import Enum


class RejectionDomainError(ValueError):
    code: str


class InvalidRejectionInputError(RejectionDomainError):
    code = "INVALID_REJECTION_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class RejectionReason(str, Enum):
    TRUCK_DIMENSIONS_EXCEEDED = "TRUCK_DIMENSIONS_EXCEEDED"
    TRUCK_WEIGHT_EXCEEDED = "TRUCK_WEIGHT_EXCEEDED"
    NON_STACKABLE_SUPPORT = "NON_STACKABLE_SUPPORT"
    FRAGILE_SUPPORT_WEIGHT_EXCEEDED = "FRAGILE_SUPPORT_WEIGHT_EXCEEDED"
    INSUFFICIENT_SUPPORT = "INSUFFICIENT_SUPPORT"
    COLLISION = "COLLISION"
    NO_VALID_POSITION = "NO_VALID_POSITION"


REJECTION_REASON_PRECEDENCE: tuple[RejectionReason, ...] = (
    RejectionReason.TRUCK_DIMENSIONS_EXCEEDED,
    RejectionReason.TRUCK_WEIGHT_EXCEEDED,
    RejectionReason.NON_STACKABLE_SUPPORT,
    RejectionReason.FRAGILE_SUPPORT_WEIGHT_EXCEEDED,
    RejectionReason.INSUFFICIENT_SUPPORT,
    RejectionReason.COLLISION,
    RejectionReason.NO_VALID_POSITION,
)

_REJECTION_REASON_RANK = {
    reason: rank for rank, reason in enumerate(REJECTION_REASON_PRECEDENCE)
}


def select_rejection_reason(
    reasons: Sequence[RejectionReason],
) -> RejectionReason:
    """Return the highest-priority approved reason, independent of input order."""

    if not isinstance(reasons, Sequence) or isinstance(
        reasons, (str, bytes, bytearray)
    ):
        raise InvalidRejectionInputError(
            "reasons", "must be an ordered sequence of RejectionReason"
        )

    validated_reasons = tuple(reasons)
    if not validated_reasons:
        raise InvalidRejectionInputError("reasons", "must not be empty")
    for position, reason in enumerate(validated_reasons):
        if not isinstance(reason, RejectionReason):
            raise InvalidRejectionInputError(
                f"reasons[{position}]", "must be a RejectionReason"
            )

    return min(validated_reasons, key=_REJECTION_REASON_RANK.__getitem__)
