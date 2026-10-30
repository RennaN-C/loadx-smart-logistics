"""Conservative multi-turn reference resolution; never uses history as facts or authority."""

import re

from app.modules.assistant.capabilities import normalize, topics
from app.modules.assistant.schemas import ChatRequest

_LATEST = re.compile(
    r"^(?:(?:o|a|os|as)\s+)?(?:ultim\w*|mais recente|anterior|penultim\w*)"
    r"(?:[.!?, ]|$)"
)
_PLAN_FOLLOWUP = re.compile(
    r"^(?:e |mas |entao |sobre isso|por que|porque|como assim|deu algum problema|"
    r"o que aconteceu|e esse|e aquele)"
)
_LATEST_PLAN_FOLLOWUP = re.compile(
    r"^(?:sobre|do|aquele|aquele do|daquele|me refiro ao)\s+"
    r"(?:o\s+)?(?:ultim\w*|planejamento|plano)\b"
)
_FLEET_REASON_FOLLOWUP = re.compile(
    r"^(?:(?:mas|e|entao)\s+)?(?:por que|porque|qual(?:\s+e)?\s+o\s+motivo|"
    r"quais\s+(?:os\s+)?motivos|o que\s+impede)"
    r".{0,120}\b(?:caminh\w*|veicul\w*|eles|esses|estas|estao|"
    r"indispon\w*|ambos)\b"
)
_FLEET_UNAVAILABLE = re.compile(
    r"\b(?:caminh\w*|veicul\w*|frota)\b.{0,110}"
    r"\b(?:indispon\w*|nao dispon\w*|bloquead\w*|fora de operac\w*)\b"
)


def fleet_reason_followup(data: ChatRequest) -> bool:
    """Only the last user topic can select a new authorized fleet read.

    History never supplies vehicle identities, permissions or reasons: those are
    retrieved again from the operational backend on every follow-up.
    """
    current = normalize(data.message)
    if not _FLEET_REASON_FOLLOWUP.search(current) or not data.history:
        return False
    previous = [normalize(item.content) for item in data.history if item.role == "user"]
    return bool(previous and _FLEET_UNAVAILABLE.search(previous[-1]))


_TRUCK_HYPOTHESIS = re.compile(
    r"\b(?:trocar|substituir|mudar|outro|outra|melhorar|melhora|compensa)\b"
    r".{0,90}\b(?:caminh\w*|veicul\w*|frota|capacidade)\b|"
    r"\b(?:caminh\w*|veicul\w*)\b.{0,75}\b(?:melhora|compensa|trocar)\b"
)


def _planning_recent(previous_questions: list[str]) -> bool:
    for previous in reversed(previous_questions[-4:]):
        previous_topics = topics(previous)
        if previous_topics - {"planning", "fleet", "loading"}:
            break
        if "planning" in previous_topics:
            return True
    return False


def resolve_followup(data: ChatRequest) -> tuple[ChatRequest, bool]:
    """Rewrite only clear planning followups into resolvable questions.

    Previous turns identify a topic, never a record id, authorization, quantity or
    operational result. The current plan id, if present, is revalidated by services.
    Explicit changes of subject take priority over any earlier planning topic.
    """
    if not data.history:
        return data, False
    current = normalize(data.message).strip()
    if not current:
        return data, False
    current_topics = topics(data.message)
    previous_questions = [
        normalize(msg.content) for msg in data.history if msg.role == "user"
    ]
    if not previous_questions:
        return data, False
    # A truck question may follow a weight question (fleet) about the same plan.
    # Do not cross an intervening order, customer, settings or other topic.
    planning_recent = _planning_recent(previous_questions)
    if current_topics - {"planning", "fleet", "loading"}:
        return data, False
    if (
        (_LATEST.search(current) or _LATEST_PLAN_FOLLOWUP.search(current))
        and planning_recent
        and not (current_topics - {"planning", "fleet", "loading"})
    ):
        return data.model_copy(
            update={"message": "Explique o último planejamento. " + data.message}
        ), True
    if planning_recent and not data.plan_id and _TRUCK_HYPOTHESIS.search(current):
        # Re-read the latest authorized snapshot instead of trusting older
        # conversational claims; do not invent a plan reference.
        return data.model_copy(
            update={
                "message": "Explique o último planejamento e responda: " + data.message
            }
        ), True
    if (
        data.plan_id
        and (_TRUCK_HYPOTHESIS.search(current) or _PLAN_FOLLOWUP.search(current))
        and (planning_recent or "planning" in current_topics or not current_topics)
    ):
        return data.model_copy(
            update={"message": "Explique esse planejamento e responda: " + data.message}
        ), True
    if (
        planning_recent
        and not current_topics
        and _PLAN_FOLLOWUP.search(current)
        and ("problema" in current or "rejeit" in current or "nao coube" in current)
    ):
        return data.model_copy(
            update={
                "message": "Explique o último planejamento e as rejeições. "
                + data.message
            }
        ), True
    return data, False
