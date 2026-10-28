"""Concise, factual replies to a question about an authorized saved plan."""

import re

from app.modules.assistant.capabilities import normalize
from app.modules.assistant.schemas import ChatResponse, Source


def _number(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return format(value, "g").replace(".", ",")


def _summary(question: str, fact: Source) -> str | None:
    values = fact.values
    loaded = _number(values.get("loaded_volumes"))
    rejected = _number(values.get("rejected_volumes"))
    if loaded is None or rejected is None:
        return None
    q = normalize(question)
    truck = values.get("truck_plate")
    vehicle = (
        f" no caminhão {truck[:16]}" if isinstance(truck, str) and truck.strip() else ""
    )
    state = {
        "CALCULATED": "calculado, ainda não aprovado",
        "APPROVED": "aprovado",
        "REJECTED": "rejeitado",
        "CANCELED": "cancelado",
    }.get(values.get("status"), "registrado")
    extras = ""
    if values.get("is_current_part") == "Não":
        extras += " Este registro não é a parte vigente da distribuição."
    if values.get("distribution_status") == "CANCELED":
        extras += " A distribuição está cancelada."
    elif values.get("distribution_status") == "INCOMPLETE":
        extras += " A distribuição está incompleta."

    changing = (
        re.search(r"\b(?:trocar|substituir|mudar|outro|outra|melhora|compensa)\b", q)
        and re.search(r"\b(?:caminh\w*|veicul\w*|frota|capacidade)\b", q)
    )
    if changing:
        if rejected == "0":
            answer = (
                f"Neste planejamento{vehicle}, os {loaded} volumes foram "
                "posicionados sem rejeições. Portanto, a troca não parece "
                "necessária apenas para acomodar a carga."
            )
        else:
            answer = (
                f"Neste planejamento{vehicle}, {loaded} volumes couberam e "
                f"{rejected} foram rejeitados. Outro caminhão pode ajudar, "
                "dependendo das restrições que causaram as rejeições."
            )
        weight = _number(values.get("weight_kg"))
        capacity = _number(values.get("truck_capacity_weight_kg"))
        if weight is not None and capacity is not None:
            answer += f" O peso registrado foi {weight} de {capacity} kg."
        return (
            answer
            + " Uma comparação dos veículos disponíveis e um novo cálculo "
            "são necessários para confirmar qualquer melhoria; não simulei a troca."
            + extras
        )

    if re.search(r"\b(?:problema|rejeit\w*|nao coube|falhou|erro)\b", q):
        if rejected == "0":
            return (
                f"No cálculo salvo{vehicle}, os {loaded} volumes couberam e "
                "nenhuma rejeição foi registrada. Isso não comprova que não houve "
                "outros problemas operacionais."
                + extras
            )
        labels = {
            "reason_TRUCK_WEIGHT_EXCEEDED": "limite de peso",
            "reason_TRUCK_DIMENSIONS_EXCEEDED": "dimensões do caminhão",
            "reason_NO_VALID_POSITION": "nenhuma posição válida",
            "reason_COLLISION": "posição sem colisão não encontrada",
        }
        reasons = [
            label for key, label in labels.items()
            if isinstance(values.get(key), (int, float)) and values[key] > 0
        ]
        reason_text = (
            " Motivos registrados: " + ", ".join(reasons) + "."
            if reasons else " Consulte os motivos no registro detalhado."
        )
        return (
            f"Neste planejamento{vehicle}, {rejected} volumes foram rejeitados "
            f"e {loaded} foram posicionados."
            + reason_text
            + extras
        )

    occupancy = _number(values.get("occupancy_percent"))
    weight = _number(values.get("weight_kg"))
    capacity = _number(values.get("truck_capacity_weight_kg"))
    answer = (
        f"O planejamento{vehicle} está {state}: "
        f"{loaded} volumes carregados e {rejected} rejeitados."
    )
    if occupancy is not None:
        answer += f" A ocupação geométrica registrada é {occupancy}%."
    if weight is not None and capacity is not None:
        answer += f" O peso é {weight} de {capacity} kg."
    return (
        answer + extras + " Esses dados vêm do cálculo salvo, não de uma nova "
        "simulação. Quer analisar as rejeições ou comparar caminhões?"
    )


def brief_verified_plan(question: str, result: ChatResponse) -> ChatResponse:
    """Preserve source records but avoid repeating a full technical report."""
    if (
        result.source != "BACKEND"
        or len(result.facts) != 1
        or result.facts[0].name != "Análise do planejamento"
    ):
        return result
    answer = _summary(question, result.facts[0])
    return result.model_copy(update={"answer": answer}) if answer else result
