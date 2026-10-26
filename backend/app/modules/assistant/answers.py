"""The model selects guidance; only the server authors factual prose and values."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.ai.provider import AIProviderUnavailableError
from app.modules.assistant.schemas import Source

GUIDANCE = {
    "facts": "Os indicadores abaixo foram consultados e calculados pelo LoadX. Confira a origem, os critérios e o período de cada consulta.",
    "query_required": "Ainda não consultei dados para confirmar esse indicador. Faça uma consulta específica; não há valor operacional confirmado nesta resposta.",
    "planning_flow": "Selecione pedidos prontos, escolha a modalidade e os veículos e calcule o planejamento. Depois da aprovação, continue pela conferência, viagem e entrega, respeitando as ações disponíveis na operação.",
    "planning_status": "Calculado é uma proposta persistida; aprovado permite continuar a operação. Aprovação não significa entrega concluída. Entrega de uma parte também não significa entrega total do pedido.",
    "capacity": "Confira os motivos de rejeição nos fatos da tentativa. Revise dimensões, peso, apoio, fragilidade e disponibilidade dos caminhões. Não force encaixes nem aumente limites para contornar uma rejeição.",
    "recovery": "Consulte Planos existentes e o estado salvo antes de repetir uma operação cujo resultado não foi confirmado. Seleções ainda não calculadas são rascunhos locais.",
    "cancellation": "Abra a distribuição e confira sua situação e as ações permitidas. Uma parte cancelada pode exigir reprocessamento antes da aprovação total; distribuições concluídas ou canceladas preservam o histórico.",
    "availability": "Consulte a disponibilidade atual da frota. Cadastro ativo e disponibilidade operacional são critérios diferentes; manutenção, documentação e conflitos podem impedir o uso de um veículo.",
    "customer_selection": "Selecione explicitamente o cliente nas opções autorizadas antes de consultar seus indicadores. Limpe o filtro para consultar outro cadastro.",
    "financial_limits": "Sem receitas, custos comparáveis e uma linha de base validada, não é possível confirmar lucro, retorno financeiro ou melhoria percentual.",
    "read_only": "Posso orientar e consultar informações autorizadas. Alterações devem ser feitas nas telas da operação, com as permissões e confirmações exigidas pelo LoadX.",
}


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
    return " ".join(GUIDANCE[code] for code in dict.fromkeys(codes))


ANSWER_CONTRACT = """
Resposta final obrigatória: somente um objeto JSON {"guidance":[...]}.
Selecione de uma a três chaves da lista abaixo. Nunca escreva texto livre,
valores, contagens, percentuais, nomes, estados de registros ou campos extras.
Indicadores são exibidos exclusivamente nos fatos calculados pelo servidor.
Para perguntas quantitativas, consulte a ferramenta autorizada antes de selecionar facts.
Sem consulta compatível, selecione query_required; nunca responda de memória/histórico.
""" + json.dumps(GUIDANCE, ensure_ascii=False)
