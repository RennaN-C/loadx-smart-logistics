from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from uuid import UUID

from app.modules.load_planning.optimizer.contracts import (
    IndividualVolume,
    VolumeIdentity,
)

ALGORITHM_VERSION = "heuristic-v1"
_OCCUPANCY_QUANTUM = Decimal("0.01")
_PERCENT_MULTIPLIER = Decimal(100)


class MetricsDomainError(ValueError):
    code: str


class InvalidMetricsInputError(MetricsDomainError):
    code = "INVALID_METRICS_INPUT"

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"{field_name} {reason}")


@dataclass(frozen=True)
class LoadMetrics:
    internal_volume_cm3: int
    used_volume_cm3: int
    total_weight_kg: Decimal
    occupancy_percent: Decimal
    loaded_count: int
    unloaded_count: int
    algorithm_version: str


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InvalidMetricsInputError(field_name, "must be a positive integer")


def _validate_volume(volume: object, field_name: str) -> IndividualVolume:
    if not isinstance(volume, IndividualVolume):
        raise InvalidMetricsInputError(field_name, "must be an IndividualVolume")
    if not isinstance(volume.identity, VolumeIdentity):
        raise InvalidMetricsInputError(
            f"{field_name}.identity", "must be a VolumeIdentity"
        )
    if not isinstance(volume.identity.order_item_id, UUID):
        raise InvalidMetricsInputError(
            f"{field_name}.identity.order_item_id", "must be a UUID"
        )
    _require_positive_int(
        volume.identity.volume_index,
        f"{field_name}.identity.volume_index",
    )
    _require_positive_int(volume.volume_cm3, f"{field_name}.volume_cm3")
    if (
        not isinstance(volume.weight_kg, Decimal)
        or not volume.weight_kg.is_finite()
        or volume.weight_kg <= 0
    ):
        raise InvalidMetricsInputError(
            f"{field_name}.weight_kg", "must be a positive finite Decimal"
        )
    return volume


def _validate_volume_sequence(
    volumes: object,
    field_name: str,
) -> tuple[IndividualVolume, ...]:
    if not isinstance(volumes, Sequence) or isinstance(
        volumes, (str, bytes, bytearray)
    ):
        raise InvalidMetricsInputError(
            field_name, "must be an ordered sequence of IndividualVolume"
        )

    validated = tuple(volumes)
    for position, volume in enumerate(validated):
        _validate_volume(volume, f"{field_name}[{position}]")
    return validated


def _ensure_unique_partition(
    placed_volumes: tuple[IndividualVolume, ...],
    rejected_volumes: tuple[IndividualVolume, ...],
) -> None:
    seen_identities: set[VolumeIdentity] = set()
    for field_name, volumes in (
        ("placed_volumes", placed_volumes),
        ("rejected_volumes", rejected_volumes),
    ):
        for position, volume in enumerate(volumes):
            if volume.identity in seen_identities:
                raise InvalidMetricsInputError(
                    f"{field_name}[{position}].identity",
                    "must be unique across placed_volumes and rejected_volumes",
                )
            seen_identities.add(volume.identity)


def _identity_key(volume: IndividualVolume) -> tuple[int, int]:
    return (volume.order_item_id.int, volume.volume_index)


def _sum_weights(volumes: tuple[IndividualVolume, ...]) -> Decimal:
    if not volumes:
        return Decimal(0)

    weights = tuple(volume.weight_kg for volume in volumes)
    minimum_exponent = min(weight.as_tuple().exponent for weight in weights)
    highest_adjusted = max(weight.adjusted() for weight in weights)
    required_precision = (
        highest_adjusted - minimum_exponent + len(str(len(weights))) + 2
    )
    calculation_context = Context(
        prec=max(28, required_precision),
        rounding=ROUND_HALF_UP,
    )
    with localcontext(calculation_context):
        return sum(weights, start=Decimal(0))


def _calculate_occupancy_percent(
    used_volume_cm3: int,
    internal_volume_cm3: int,
) -> Decimal:
    if used_volume_cm3 == 0:
        return Decimal("0.00")

    required_precision = len(str(used_volume_cm3)) + len(str(internal_volume_cm3)) + 6
    calculation_context = Context(
        prec=max(28, required_precision),
        rounding=ROUND_HALF_UP,
    )
    with localcontext(calculation_context):
        percentage = (
            Decimal(used_volume_cm3)
            * _PERCENT_MULTIPLIER
            / Decimal(internal_volume_cm3)
        )
        return percentage.quantize(_OCCUPANCY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_load_metrics(
    *,
    internal_volume_cm3: int,
    placed_volumes: Sequence[IndividualVolume],
    rejected_volumes: Sequence[IndividualVolume],
) -> LoadMetrics:
    _require_positive_int(internal_volume_cm3, "internal_volume_cm3")
    placed = _validate_volume_sequence(placed_volumes, "placed_volumes")
    rejected = _validate_volume_sequence(rejected_volumes, "rejected_volumes")
    _ensure_unique_partition(placed, rejected)

    ordered_placed = tuple(sorted(placed, key=_identity_key))
    used_volume_cm3 = sum(volume.volume_cm3 for volume in ordered_placed)
    if used_volume_cm3 > internal_volume_cm3:
        raise InvalidMetricsInputError(
            "placed_volumes",
            "total volume must not exceed internal_volume_cm3",
        )

    return LoadMetrics(
        internal_volume_cm3=internal_volume_cm3,
        used_volume_cm3=used_volume_cm3,
        total_weight_kg=_sum_weights(ordered_placed),
        occupancy_percent=_calculate_occupancy_percent(
            used_volume_cm3,
            internal_volume_cm3,
        ),
        loaded_count=len(placed),
        unloaded_count=len(rejected),
        algorithm_version=ALGORITHM_VERSION,
    )
