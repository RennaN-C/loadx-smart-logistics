"""Audited, bounded planning history and explanation based on persisted facts.

The LLM is not allowed to select arbitrary plans or invent optimizer decisions.
All reads go through the existing planning service and its role restrictions.
"""

import re
import uuid
from collections import Counter

from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.pagination import PaginationParams
from app.modules.access_profiles.catalog import has_permission
from app.modules.load_planning.service import (
    LoadPlanNotFoundError,
    LoadPlanningService,
)
from app.modules.users.models import User

from .schemas import ChatRequest, ChatResponse, Source

_PLAN_WORD = re.compile(
    r"\b(?:plano|planos|planejament\w*|calcul\w*|c[aá]lcul\w*|"
    r"otimiz\w*|algoritmo|distribui\w*)\b", re.IGNORECASE
)
_EXPLAIN_WORD = re.compile(
    r"\b(?:explic\w*|analis\w*|por que|porque|como|resultado|"
    r"rejeit\w*|n[aã]o coube|sobr\w*|ocupa\w*|coub\w*)\b",
    re.IGNORECASE,
)
_LATEST_WORD = re.compile(
    r"\b(?:[uú]ltim\w*|mais recente|recente|anterior|pen[uú]ltim\w*)\b",
    re.IGNORECASE,
)
_LIST_WORD = re.compile(
    r"\b(?:list\w*|mostr\w*|tod\w*|hist[oó]rico|quais|"
    r"cadastrad\w*|salv\w*)\b", re.IGNORECASE
)
_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_REASONS = {
    "TRUCK_DIMENSIONS_EXCEEDED": "dimensões superiores às do caminhão",
    "TRUCK_WEIGHT_EXCEEDED": "limite de peso do caminhão",
    "NON_STACKABLE_SUPPORT": "apoio em carga não empilhável",
    "FRAGILE_SUPPORT_WEIGHT_EXCEEDED": "peso incompatível com apoio frágil",
    "INSUFFICIENT_SUPPORT": "superfície de apoio insuficiente",
    "COLLISION": "não foi encontrada posição sem colisão",
    "NO_VALID_POSITION": "nenhuma posição válida foi encontrada",
}
_PLAN_STATES = {
    "CALCULATED": "calculado (ainda não aprovado)",
    "APPROVED": "aprovado",
    "REJECTED": "rejeitado",
    "CANCELED": "cancelado",
}
_DIST_STATES = {"CANCELED": "cancelada", "INCOMPLETE": "incompleta"}


def _page(question: str) -> int:
    match = re.search(r"\bp[aá]gina\s+(\d{1,3})\b", question, re.IGNORECASE)
    return min(max(int(match.group(1)), 1), 100) if match else 1


def _kind(question: str, data: ChatRequest) -> str | None:
    text = question.casefold()
    # A route context by itself is not a request to fetch every plan.
    if _UUID.search(text):
        return "explain"
    if data.plan_id and _EXPLAIN_WORD.search(text):
        return "explain"
    if not _PLAN_WORD.search(text):
        return None
    if _LATEST_WORD.search(text) or _EXPLAIN_WORD.search(text):
        return "explain"
    if _LIST_WORD.search(text):
        return "list"
    return None


def planning_insight(db: Session, user: User, data: ChatRequest) -> ChatResponse | None:
    kind = _kind(data.message, data)
    if kind is None:
        return None
    if not has_permission(user, "loadx.planning.read"):
        return ChatResponse(
            source="GUARDRAIL",
            answer="Seu perfil não permite consultar planejamentos.",
        )
    svc = LoadPlanningService(db)
    page_number = _page(data.message)
    if kind == "list":
        page = svc.list_load_plans(
            PaginationParams(page=page_number, page_size=8, sort_order="desc"),
            requester_role=user.role,
        )
        values: dict[str, int | float | str | None] = {
            "total_records": page.total,
            "page": page.page,
            "total_pages": page.total_pages,
        }
        links: list[dict[str, str]] = []
        for idx, plan in enumerate(page.items, 1):
            status = _PLAN_STATES.get(plan.status, plan.status)
            values[f"item_{idx}"] = (
                f"{plan.truck_plate[:16]} · {status} · "
                f"{plan.loaded_count} carregados, {plan.unloaded_count} rejeitados"
            )
            links.append(
                {"label": f"Abrir plano {idx} · {plan.truck_plate[:16]}",
                 "href": f"/planning/{plan.id}"}
            )
        answer = (
            f"Encontrei {page.total} planejamentos autorizados. "
            f"Página {page.page} de {page.total_pages} (mais recentes primeiro). "
            "Abra um plano para analisar seu cálculo em detalhes."
            if page.total else "Nenhum planejamento disponível para seu perfil."
        )
        return ChatResponse(
            source="BACKEND",
            answer=answer,
            facts=[Source(
                name="Histórico de planejamentos",
                criteria="Registros persistidos mais recentes primeiro; até oito por página. "
                "O Conferente visualiza apenas planos aprovados e ativos. "
                "Planos cancelados permanecem no histórico de perfis autorizados.",
                values=values, links=links,
            )],
        )

    match = _UUID.search(data.message)
    plan_id = uuid.UUID(match.group()) if match else data.plan_id
    if plan_id is None:
        # Never guess an arbitrary plan from conversation history or model text.
        offset = 2 if re.search(r"\b(?:pen[uú]ltim\w*|anterior)\b", data.message, re.IGNORECASE) else 1
        page = svc.list_load_plans(
            PaginationParams(page=1, page_size=offset, sort_order="desc"),
            requester_role=user.role,
        )
        if len(page.items) < offset:
            return ChatResponse(
                source="BACKEND",
                answer="Não encontrei esse planejamento entre os registros que seu perfil pode consultar.",
            )
        plan_id = page.items[offset - 1].id
    try:
        plan = svc.get_load_plan(plan_id)
    except LoadPlanNotFoundError:
        raise ApiError(404, "LOAD_PLAN_NOT_FOUND", "Planejamento não encontrado.") from None
    if user.role == "CHECKER" and plan.status != "APPROVED":
        raise ApiError(403, "AUTH_FORBIDDEN", "Planejamento não autorizado.")
    dist_id, dist_status, part_status, is_current = svc.get_distribution_state_for_plan(plan.id)
    reasons = Counter(
        item.rejection_reason for item in plan.items if item.rejection_reason
    )
    weight = float(plan.total_weight_kg)
    limit = float(plan.truck_snapshot_max_weight_kg)
    occupied = float(plan.occupancy_percent)
    status = _PLAN_STATES.get(plan.status, plan.status)
    details = ", ".join(
        f"{quantity} × {_REASONS.get(reason, reason)}"
        for reason, quantity in reasons.items()
    ) if reasons else "nenhuma rejeição registrada"
    note = (
        "Essa versão não é mais a parte vigente da distribuição. "
        if not is_current else ""
    )
    if dist_status in _DIST_STATES:
        note += f"A distribuição está {_DIST_STATES[dist_status]}; não está disponível como plano operacional ativo. "
    explain = (
        f"Analisei o planejamento salvo do caminhão {plan.truck_snapshot_plate[:16]}. "
        f"Situação: {status}. O algoritmo {plan.algorithm_version[:64]} "
        f"posicionou {plan.loaded_count} volumes e rejeitou {plan.unloaded_count}. "
        f"Ocupação geométrica: {occupied:g}%; peso: {weight:g} de {limit:g} kg. "
        f"Motivos registrados: {details}. "
        + note
        + "Esses são resultados persistidos, não uma nova simulação: o registro "
        "não comprova que esse era o único ou o melhor arranjo possível."
    )
    values: dict[str, int | float | str | None] = {
        "status": plan.status,
        "loaded_volumes": plan.loaded_count,
        "rejected_volumes": plan.unloaded_count,
        "occupancy_percent": occupied,
        "weight_kg": weight,
        "truck_capacity_weight_kg": limit,
        "algorithm_version": plan.algorithm_version[:64],
        "truck_plate": plan.truck_snapshot_plate[:16],
        "internal_width_cm": plan.truck_snapshot_internal_width_cm,
        "internal_height_cm": plan.truck_snapshot_internal_height_cm,
        "internal_length_cm": plan.truck_snapshot_internal_length_cm,
        "is_current_part": "Sim" if is_current else "Não",
        "distribution_status": dist_status,
        "part_status": part_status,
    }
    for reason, quantity in reasons.items():
        values[f"reason_{reason}"] = quantity
    link = {"label": "Abrir planejamento e ações permitidas",
            "href": f"/planning/{plan.id}"}
    return ChatResponse(
        source="BACKEND",
        answer=explain,
        facts=[Source(
            name="Análise do planejamento",
            criteria="Snapshot persistido do algoritmo. Versão, volumes, posições, "
            "ocupação, peso e motivos de rejeição vêm do banco. "
            "A ferramenta não recalcula nem aprova um plano.",
            values=values, links=[link],
        )],
    )
