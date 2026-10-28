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
_TRUCK_HYPOTHESIS = re.compile(
    r"\b(?:trocar|substituir|mudar|outro|outra|melhorar|melhora|compensa)\b"
    r".{0,90}\b(?:caminh\w*|veicul\w*|frota|capacidade)\b|"
    r"\b(?:caminh\w*|veicul\w*)\b.{0,75}\b(?:melhora|compensa|trocar)\b"
)


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
    last = previous_questions[-1]
    # The most recent explicit user topic controls context; never inherit an older
    # planning topic after a customer, order or settings discussion.
    previous_explicit = next(
        (topics(text) for text in reversed(previous_questions) if topics(text)),
        set(),
    )
    planning_recent = "planning" in previous_explicit
    if current_topics - {"planning", "fleet", "loading"}:
        return data, False
    if _LATEST.search(current) and planning_recent and not current_topics:
        return data.model_copy(
            update={"message": "Explique o último planejamento. " + data.message}
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
            update={"message": "Explique o último planejamento e as rejeições. " + data.message}
        ), True
    return data, False
