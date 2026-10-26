"""Resolve only authorized, persisted context; no client-supplied plan facts."""

from collections import Counter

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.modules.access_profiles.catalog import has_permission
from app.modules.load_planning.distribution_service import (
    DistributionError,
    LoadDistributionService,
)
from app.modules.load_planning.service import LoadPlanningService, LoadPlanNotFoundError
from app.modules.users.models import User

from .schemas import ChatRequest, Source


def planning_context(
    db: Session, user: User, data: ChatRequest
) -> tuple[list[Source], list[dict]]:
    facts: list[Source] = []
    links: list[dict] = []
    if not data.plan_id and not data.distribution_id:
        return facts, links
    if not has_permission(user, "loadx.planning.read"):
        raise ApiError(
            403, "AUTH_FORBIDDEN", "Você não pode consultar este planejamento."
        )
    if data.plan_id:
        try:
            plan = LoadPlanningService(db).get_load_plan(data.plan_id)
        except LoadPlanNotFoundError:
            raise ApiError(
                404, "LOAD_PLAN_NOT_FOUND", "Plano não encontrado."
            ) from None
        if user.role == "CHECKER" and plan.status != "APPROVED":
            raise ApiError(
                403, "AUTH_FORBIDDEN", "Este plano não está disponível para seu perfil."
            )
        reasons = Counter(
            item.rejection_reason for item in plan.items if item.rejection_reason
        )
        facts.append(
            Source(
                name="Plano autorizado",
                criteria="Snapshot persistido; cálculo independente da IA, limite de 200 volumes totais. Aprovação não significa entrega concluída.",
                values={
                    "status": plan.status,
                    "loaded_volumes": plan.loaded_count,
                    "rejected_volumes": plan.unloaded_count,
                    "occupancy_percent": float(plan.occupancy_percent),
                    "weight_kg": float(plan.total_weight_kg),
                    "truck_capacity_weight_kg": float(
                        plan.truck_snapshot_max_weight_kg
                    ),
                    "internal_width_cm": plan.truck_snapshot_internal_width_cm,
                    "internal_height_cm": plan.truck_snapshot_internal_height_cm,
                    "internal_length_cm": plan.truck_snapshot_internal_length_cm,
                    **dict(reasons),
                },
            )
        )
        links.append({"label": "Abrir plano", "href": f"/planning/{plan.id}"})
    if data.distribution_id:
        try:
            distribution = LoadDistributionService(db).get(data.distribution_id)
        except DistributionError:
            raise ApiError(
                404, "DISTRIBUTION_NOT_FOUND", "Distribuição não encontrada."
            ) from None
        if user.role == "CHECKER" and distribution.status != "APPROVED":
            raise ApiError(
                403,
                "AUTH_FORBIDDEN",
                "Esta distribuição não está disponível para seu perfil.",
            )
        if data.plan_id and not any(
            part.load_plan.id == data.plan_id for part in distribution.parts
        ):
            raise ApiError(
                422,
                "ASSISTANT_CONTEXT_MISMATCH",
                "O plano não pertence à distribuição informada.",
            )
        facts.append(
            Source(
                name="Distribuição autorizada",
                criteria="Cada volume físico pertence a uma única parte; somente ações permitidas na tela operacional. Nenhuma ação é executada pelo assistente.",
                values={
                    "status": distribution.status,
                    "truck_count": distribution.truck_count,
                    "volume_count": distribution.volume_count,
                },
            )
        )
        links.append(
            {
                "label": "Abrir distribuição",
                "href": f"/planning/distributions/{distribution.id}",
            }
        )
    return facts, links
