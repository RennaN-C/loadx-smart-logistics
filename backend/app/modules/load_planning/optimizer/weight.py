from decimal import Decimal


class WeightDomainError(ValueError):
    pass


class InvalidWeightInputError(WeightDomainError):
    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


class WeightLimitExceededError(WeightDomainError):
    def __init__(
        self,
        current_weight_kg: Decimal,
        candidate_weight_kg: Decimal,
        max_weight_kg: Decimal,
    ) -> None:
        self.current_weight_kg = current_weight_kg
        self.candidate_weight_kg = candidate_weight_kg
        self.max_weight_kg = max_weight_kg
        self.next_total_weight_kg = current_weight_kg + candidate_weight_kg
        super().__init__("candidate weight exceeds the truck maximum weight")


def _require_finite_decimal(value: object, field_name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise InvalidWeightInputError(field_name, "must be a Decimal")
    if not value.is_finite():
        raise InvalidWeightInputError(field_name, "must be finite")
    return value


def calculate_next_weight(
    current_weight_kg: Decimal,
    candidate_weight_kg: Decimal,
    max_weight_kg: Decimal,
) -> Decimal:
    current_weight = _require_finite_decimal(current_weight_kg, "current_weight_kg")
    candidate_weight = _require_finite_decimal(
        candidate_weight_kg, "candidate_weight_kg"
    )
    max_weight = _require_finite_decimal(max_weight_kg, "max_weight_kg")

    if max_weight <= 0:
        raise InvalidWeightInputError("max_weight_kg", "must be greater than zero")
    if current_weight < 0:
        raise InvalidWeightInputError(
            "current_weight_kg", "must be greater than or equal to zero"
        )
    if current_weight > max_weight:
        raise InvalidWeightInputError(
            "current_weight_kg", "must not exceed max_weight_kg"
        )
    if candidate_weight <= 0:
        raise InvalidWeightInputError(
            "candidate_weight_kg", "must be greater than zero"
        )

    next_total_weight = current_weight + candidate_weight
    if next_total_weight > max_weight:
        raise WeightLimitExceededError(current_weight, candidate_weight, max_weight)
    return next_total_weight
