"""The model selects guidance; only the server authors factual prose and values."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.ai.provider import AIProviderUnavailableError
from app.modules.assistant.schemas import Source

GUIDANCE = {
    "facts": "Consultei os registros autorizados. Os detalhes abaixo mostram a origem, os critérios e o período da consulta.",
    "query_required": "Ainda não tenho dados suficientes para confirmar essa informação. Informe qual indicador ou operação deseja consultar.",
    "planning_flow": "Para planejar: selecione pedidos prontos, escolha veículos e calcule. Confira o resultado, aprove quando estiver correto e siga para conferência, viagem e entrega.",
    "planning_status": "Um cálculo salvo não é uma aprovação. Aprovar permite avançar no processo, mas a entrega só termina quando a operação é concluída.",
    "capacity": "Se a carga não coube, confira os motivos apontados na tentativa. Verifique peso, dimensões, colisões e veículos disponíveis antes de ajustar o planejamento.",
    "recovery": "Antes de repetir uma operação, confira o último plano salvo. Uma seleção que ainda não foi calculada é apenas um rascunho.",
    "cancellation": "Consulte a situação da distribuição antes de agir. Cancelamentos permanecem no histórico e podem exigir novo planejamento.",
    "availability": "Verifique a disponibilidade da frota. Mesmo um veículo ativo pode estar impedido por manutenção, documentação ou conflito de agenda.",
    "customer_selection": "Há mais de uma opção de cliente. Selecione o cadastro correto para aplicar o filtro à consulta.",
    "financial_limits": "Não há dados financeiros e base de comparação suficientes para confirmar economia, lucro ou retorno.",
    "read_only": "Posso consultar dados e orientar próximos passos. Para modificar registros, utilize a tela correspondente e suas confirmações.",
}


# Somente estes dados numéricos, vindos de ferramentas autorizadas do backend,
# podem aparecer no texto. Nunca interpretar strings livres do modelo como números.
_HIGHLIGHTS = {
    "fully_delivered_orders": (
        "pedido totalmente entregue",
        "pedidos totalmente entregues",
    ),
    "dispatched_orders": ("pedido expedido", "pedidos expedidos"),
    "trips_started": ("viagem iniciada", "viagens iniciadas"),
    "trips_finished": ("viagem concluída", "viagens concluídas"),
    "remaining_volumes": ("volume sem posição segura", "volumes sem posição segura"),
    "loaded_volumes": ("volume carregado", "volumes carregados"),
    "rejected_volumes": ("volume rejeitado", "volumes rejeitados"),
}


def factual_highlights(facts: list[Source]) -> str:
    statements: list[str] = []
    for fact in facts:
        for key, labels in _HIGHLIGHTS.items():
            value = fact.values.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                label = labels[0] if value == 1 else labels[1]
                statements.append(f"{value:,} {label}".replace(",", "."))
                if len(statements) == 2:
                    return (
                        "Resultado confirmado pelo LoadX: "
                        + "; ".join(statements)
                        + "."
                    )
    return (
        "Resultado confirmado pelo LoadX: " + "; ".join(statements) + "."
        if statements
        else ""
    )


class AnswerSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guidance: list[
        Literal[
            "facts",
            "query_required",
            "planning_flow",
            "planning_status",
            "capacity",
            "recovery",
            "cancellation",
            "availability",
            "customer_selection",
            "financial_limits",
            "read_only",
        ]
    ] = Field(min_length=1, max_length=3)


def grounded_answer(content: str, facts: list[Source]) -> str:
    """No model-authored strings or quantities cross the public response boundary."""
    selection = AnswerSelection.model_validate(json.loads(content))
    if len(set(selection.guidance)) != len(selection.guidance):
        raise AIProviderUnavailableError
    codes = [
        "query_required" if code == "facts" and not facts else code
        for code in selection.guidance
    ]
    intro = factual_highlights(facts) if "facts" in codes else ""
    details = " ".join(GUIDANCE[code] for code in dict.fromkeys(codes))
    return "\n\n".join(part for part in (intro, details) if part)


ANSWER_CONTRACT = """
Resposta final obrigatória: somente um objeto JSON {"guidance":[...]}.
Selecione de uma a três chaves da lista abaixo. Nunca escreva texto livre,
valores, contagens, percentuais, nomes, estados de registros ou campos extras.
Indicadores são exibidos exclusivamente nos fatos calculados pelo servidor.
Para perguntas quantitativas, consulte a ferramenta autorizada antes de selecionar facts.
Sem consulta compatível, selecione query_required; nunca responda de memória/histórico.
""" + json.dumps(GUIDANCE, ensure_ascii=False)
