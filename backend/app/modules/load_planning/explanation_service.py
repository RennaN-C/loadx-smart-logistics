import uuid
from collections import Counter
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AIExplanationContext,
    AIPlacedVolumeContext,
    AIProvider,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIRejectedVolumeContext,
    AITruckContext,
    validate_ai_provider_output,
)
from app.modules.load_planning.explanation import (
    LoadPlanExplanationContext,
    build_load_plan_explanation_context,
)
from app.modules.load_planning.optimizer.rejections import (
    REJECTION_REASON_PRECEDENCE,
)
from app.modules.load_planning.repository import LoadPlanRepository

ExplanationSource = Literal["AI", "FALLBACK"]
_EXPLANATION_ROLES = frozenset({"ADMIN", "CHECKER", "LOGISTICS_MANAGER"})


class LoadPlanExplanationNotFoundError(Exception):
    pass


class LoadPlanExplanationForbiddenError(Exception):
    pass


class LoadPlanExplanationInvalidPlanError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class LoadPlanExplanationResult:
    load_plan_id: uuid.UUID
    source: ExplanationSource
    explanation: str
    algorithm_version: str


class LoadPlanExplanationService:
    def __init__(
        self,
        db: Session,
        provider: AIProvider,
        *,
        timeout_seconds: float,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a positive finite number")
        self.repository = LoadPlanRepository(db)
        self.provider = provider
        self.timeout_seconds = float(timeout_seconds)

    def explain(
        self,
        load_plan_id: uuid.UUID,
        *,
        requester_role: str,
    ) -> LoadPlanExplanationResult:
        load_plan = self.repository.get(load_plan_id)
        if load_plan is None:
            raise LoadPlanExplanationNotFoundError
        if requester_role not in _EXPLANATION_ROLES:
            raise LoadPlanExplanationForbiddenError
        if requester_role == "CHECKER" and load_plan.status != "APPROVED":
            raise LoadPlanExplanationForbiddenError

        try:
            snapshot = build_load_plan_explanation_context(load_plan)
            provider_context = _build_provider_context(snapshot)
        except (TypeError, ValueError, ValidationError) as exc:
            raise LoadPlanExplanationInvalidPlanError(str(exc)) from exc

        try:
            untrusted_output = self.provider.explain_load_plan(
                provider_context,
                timeout_seconds=self.timeout_seconds,
            )
            output = validate_ai_provider_output(untrusted_output)
        except (
            AIProviderTimeoutError,
            AIProviderUnavailableError,
            ValidationError,
        ):
            return _fallback_result(snapshot, provider_context)

        return LoadPlanExplanationResult(
            load_plan_id=snapshot.load_plan_id,
            source="AI",
            explanation=output.explanation,
            algorithm_version=snapshot.algorithm_version,
        )


def _build_provider_context(
    snapshot: LoadPlanExplanationContext,
) -> AIExplanationContext:
    return AIExplanationContext(
        truck=AITruckContext(
            internal_width_cm=snapshot.truck.internal_width_cm,
            internal_height_cm=snapshot.truck.internal_height_cm,
            internal_length_cm=snapshot.truck.internal_length_cm,
            max_weight_kg=snapshot.truck.max_weight_kg,
        ),
        internal_volume_cm3=snapshot.internal_volume_cm3,
        used_volume_cm3=snapshot.used_volume_cm3,
        occupancy_percent=snapshot.occupancy_percent,
        total_weight_kg=snapshot.total_weight_kg,
        loaded_count=snapshot.loaded_count,
        unloaded_count=snapshot.unloaded_count,
        algorithm_version=snapshot.algorithm_version,
        placed_volumes=tuple(
            AIPlacedVolumeContext(
                original_width_cm=item.volume.original_width_cm,
                original_height_cm=item.volume.original_height_cm,
                original_length_cm=item.volume.original_length_cm,
                weight_kg=item.volume.weight_kg,
                fragile=item.volume.fragile,
                stackable=item.volume.stackable,
                rotation_allowed=item.volume.rotation_allowed,
                delivery_sequence=item.volume.delivery_sequence,
                x_cm=item.x_cm,
                y_cm=item.y_cm,
                z_cm=item.z_cm,
                width_cm=item.width_cm,
                height_cm=item.height_cm,
                length_cm=item.length_cm,
                rotation_code=item.rotation_code,
                loading_sequence=item.loading_sequence,
            )
            for item in snapshot.placed_items
        ),
        rejected_volumes=tuple(
            AIRejectedVolumeContext(
                original_width_cm=item.volume.original_width_cm,
                original_height_cm=item.volume.original_height_cm,
                original_length_cm=item.volume.original_length_cm,
                weight_kg=item.volume.weight_kg,
                fragile=item.volume.fragile,
                stackable=item.volume.stackable,
                rotation_allowed=item.volume.rotation_allowed,
                delivery_sequence=item.volume.delivery_sequence,
                rejection_reason=item.rejection_reason,
            )
            for item in snapshot.rejected_items
        ),
    )


def _fallback_result(
    snapshot: LoadPlanExplanationContext,
    provider_context: AIExplanationContext,
) -> LoadPlanExplanationResult:
    counts = Counter(
        item.rejection_reason for item in provider_context.rejected_volumes
    )
    ordered_rejections = ", ".join(
        f"{reason.value}={counts[reason.value]}"
        for reason in REJECTION_REASON_PRECEDENCE
        if counts[reason.value] > 0
    )
    rejection_summary = ordered_rejections or "nenhuma"
    explanation = (
        f"Plano calculado por {snapshot.algorithm_version}: "
        f"{snapshot.loaded_count} de "
        f"{snapshot.loaded_count + snapshot.unloaded_count} volumes carregados; "
        f"ocupacao {snapshot.occupancy_percent}% e peso total "
        f"{snapshot.total_weight_kg} kg. Rejeicoes: {rejection_summary}."
    )
    return LoadPlanExplanationResult(
        load_plan_id=snapshot.load_plan_id,
        source="FALLBACK",
        explanation=explanation,
        algorithm_version=snapshot.algorithm_version,
    )
