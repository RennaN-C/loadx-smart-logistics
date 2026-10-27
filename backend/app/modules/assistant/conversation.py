"""Deterministic conversational help and permission-aware action handoff.

Write operations are deliberately *not* wired to chat. An operational action
must use the existing authenticated form, CSRF, business rules and confirmation.
"""

import re
import unicodedata

from app.modules.access_profiles.catalog import has_permission
from app.modules.assistant.schemas import ChatResponse
from app.modules.users.models import User


def _normalize(question: str) -> str:
    raw = unicodedata.normalize("NFKD", question.casefold())
    return " ".join(
        "".join(char for char in raw if not unicodedata.combining(char)).split()
    )


def conversation_reply(user: User, message: str) -> ChatResponse | None:
    text = _normalize(message).strip(" ?!.")
    greeting = {
        "oi",
        "ola",
        "ola loxi",
        "oi loxi",
        "bom dia",
        "boa tarde",
        "boa noite",
        "tudo bem",
        "e ai",
        "hey",
        "olá",
    }
    if text in greeting:
        return ChatResponse(
            source="BACKEND",
            answer=(
                "Olá! Sou o Loxi, assistente do LoadX. Posso conversar sobre a "
                "operação, consultar cadastros e indicadores autorizados e explicar "
                "planejamentos salvos. Se quiser, peça sugestões de perguntas."
            ),
        )
    if re.fullmatch(
        r"(?:obrigad[oa]|valeu|muito obrigado|muito obrigada|show|beleza)", text
    ):
        return ChatResponse(
            source="BACKEND",
            answer="Por nada! Quer analisar outro planejamento ou tirar alguma dúvida sobre a operação?",
        )
    if re.search(
        r"\b(?:sugest(?:ao|oes)|exemplos?|o que (?:voce|vc) (?:faz|sabe|pode)|"
        r"como (?:posso|comeco) perguntar|me ajude|ajuda no chat)\b",
        text,
    ):
        options: list[str] = []
        if has_permission(user, "loadx.planning.read"):
            options.extend(
                [
                    "Qual foi o último planejamento calculado?",
                    "Liste os planejamentos anteriores.",
                    "Por que houve volumes rejeitados no último cálculo?",
                ]
            )
        if has_permission(user, "loadx.products.read"):
            options.append("Quais produtos estão cadastrados?")
        if has_permission(user, "loadx.trucks.read"):
            options.append("Quais caminhões estão indisponíveis?")
        if has_permission(user, "loadx.deliveries.read"):
            options.append("Quantos pedidos foram entregues nos últimos 30 dias?")
        return ChatResponse(
            source="BACKEND",
            answer=(
                "Você pode perguntar, por exemplo:\n"
                + (
                    "\n".join(f"• {item}" for item in options[:6])
                    if options
                    else "• Como funciona o fluxo de carregamento?"
                )
                + "\n\nPara ações que alteram dados, posso orientar a tela correta; "
                "a confirmação deve ser feita no sistema."
            ),
        )
    actions = (
        ("aprovar", "loadx.planning.approve", "/planning", "aprovação de planejamento"),
        (
            "recalcular",
            "loadx.planning.create",
            "/planning",
            "recálculo de planejamento",
        ),
        (
            "cancelar",
            "loadx.planning.approve",
            "/planning",
            "cancelamento de planejamento",
        ),
        ("excluir", "loadx.products.manage", "/products", "exclusão de cadastro"),
    )
    # No implicit execution: a text command is an invitation to a reviewed UI flow.
    for verb, permission, href, label in actions:
        if re.search(rf"\b{verb}\b", text) and (
            "plano" in text or "planej" in text or "cadastro" in text
        ):
            if not has_permission(user, permission):
                return ChatResponse(
                    source="GUARDRAIL",
                    answer="Seu perfil não tem permissão para essa ação.",
                )
            return ChatResponse(
                source="BACKEND",
                answer=(
                    f"Posso te levar à tela de {label}. "
                    "Nenhum registro foi alterado pelo chat. Confira o registro, "
                    "as regras de negócio e a confirmação exigida antes de continuar."
                ),
                links=[{"label": "Abrir tela da operação", "href": href}],
            )
    return None
