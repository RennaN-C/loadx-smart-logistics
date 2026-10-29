"""Auditable documentation registry. No permission, endpoint or data invented by the model."""

import re
import unicodedata
from dataclasses import dataclass

from app.modules.access_profiles.catalog import has_permission
from app.modules.assistant.schemas import ChatRequest, ChatResponse, Source
from app.modules.users.models import User


@dataclass(frozen=True)
class Capability:
    key: str
    title: str
    permission: str | None
    route: str
    endpoint: str
    guide: str
    aliases: str
    admin: bool = False


CAPABILITIES = (
    Capability(
        "account",
        "Conta e segurança",
        None,
        "/account",
        "/auth/me",
        "Em Meu perfil, abra Conta e segurança para alterar a senha e revisar MFA, sessões e dispositivos confiáveis. Siga as confirmações e validações da tela; não informe senhas, códigos de autenticação ou tokens no chat.",
        r"minha conta|meu perfil|senha|mfa|sess[oõ]es|dispositivo confi[aá]vel",
    ),
    Capability(
        "settings",
        "Configurações",
        "loadx.settings.manage",
        "/settings",
        "/company-profile",
        "Configurações reúne conta e administração, gestão de usuários, dados da empresa, integrações, fila de eventos e configurações do LoadX. Dados institucionais e administração são exclusivos do ADMIN. Abra a seção desejada; alterações são feitas nos formulários, nunca pelo chat.",
        r"configura\w*|empresa",
        True,
    ),
    Capability(
        "profiles",
        "Perfis e permissões",
        "loadx.profiles.manage",
        "/settings#settings-users",
        "/access-profiles",
        "Perfis controlam permissões efetivas. O ADMIN gerencia usuários e perfis nas configurações. Um nome de perfil não concede acesso: cada operação revalida suas permissões no servidor.",
        r"perfis|perfil de acesso|permiss\w*",
        True,
    ),
    Capability(
        "users",
        "Usuários",
        "loadx.users.manage",
        "/settings#settings-users",
        "/users",
        "O ADMIN consulta e gerencia contas nas configurações. Alterações de acesso exigem os formulários e validações existentes; o chat não cria usuários nem muda permissões.",
        r"usu[aá]ri\w*",
        True,
    ),
    Capability(
        "products",
        "Produtos",
        "loadx.products.read",
        "/products",
        "/products",
        "Produtos guarda dimensões em centímetros, peso em quilogramas e regras de fragilidade, empilhamento e rotação. Cadastro não é controle de estoque. Consulte a lista, abra o formulário e revise as medidas antes de usar o produto em pedidos.",
        r"produt\w*|mercador\w*",
    ),
    Capability(
        "customers",
        "Clientes e endereços",
        "loadx.customers.read",
        "/contacts?tab=customers",
        "/customers",
        "Clientes podem ter vários endereços. No pedido, selecione o endereço de entrega; seu snapshot preserva o destino histórico. Arquivar um cadastro não apaga pedidos antigos.",
        r"client\w*|endere[cç]\w*",
    ),
    Capability(
        "drivers",
        "Motoristas",
        "loadx.drivers.read",
        "/contacts?tab=drivers",
        "/drivers",
        "Motoristas têm cadastro, documentos e disponibilidade. Ativo não significa disponível: pendências documentais e conflitos operacionais podem impedir novas viagens. Revise o cadastro e os bloqueios na tela correspondente.",
        r"motorist\w*|cnh",
    ),
    Capability(
        "fleet",
        "Frota",
        "loadx.trucks.read",
        "/trucks",
        "/trucks",
        "A frota reúne caminhões, capacidade, disponibilidade, documentos e manutenções. Cadastro arquivado não pode operar; manutenção e conflitos são bloqueios temporários distintos. Confira a disponibilidade antes de planejar.",
        r"frota|caminh\w*|ve[ií]cul\w*",
    ),
    Capability(
        "orders",
        "Pedidos",
        "loadx.orders.read",
        "/orders",
        "/orders",
        "O pedido reúne cliente, endereço de entrega e produtos com suas quantidades. Prepare o pedido antes de selecionar seus volumes no planejamento. Planejado não significa entregue; a situação acompanha as operações reais.",
        r"pedid\w*",
    ),
    Capability(
        "planning",
        "Planejamento",
        "loadx.planning.read",
        "/planning",
        "/load-plans",
        "Planejamento permite consultar planos salvos ou calcular uma proposta para um ou vários caminhões. Confira rejeições, peso, ocupação e o 3D antes de aprovar. A aprovação não equivale à entrega. O algoritmo é heurístico: não há prova de ótimo global.",
        r"planej\w*|plano\w*|algoritm\w*|otimiz\w*|distribui\w*|carga\w*",
    ),
    Capability(
        "loading",
        "Conferência e carregamento",
        "loadx.loading.read",
        "/loading-sessions",
        "/loading-sessions",
        "A conferência identifica os volumes do plano aprovado e registra o carregamento. Reabra sessões existentes pela central; respeite a sequência e as ações permitidas para o estado atual.",
        r"carregament\w*|confer[eê]nc\w*",
    ),
    Capability(
        "trips",
        "Viagens",
        "loadx.trips.read",
        "/trips",
        "/trips",
        "Viagens vinculam carregamento, veículo e motorista. Reabra a viagem existente para acompanhar sua situação; iniciar ou concluir exige as condições operacionais e confirmação nas telas.",
        r"viage\w*|viagem",
    ),
    Capability(
        "deliveries",
        "Entregas",
        "loadx.deliveries.read",
        "/deliveries",
        "/deliveries",
        "Entregas registram o resultado operacional e evidências. Uma perna concluída não equivale a um pedido totalmente entregue quando há distribuição entre veículos. Confira o detalhamento antes de interpretar o estado do pedido.",
        r"entreg\w*|comprovant\w*",
    ),
    Capability(
        "agenda",
        "Agenda operacional",
        "loadx.trips.read",
        "/agenda",
        "/operations/agenda",
        "A agenda organiza operações por período e pelos filtros existentes. Consulte os registros de origem para executar ações; a agenda não altera automaticamente horários ou permissões.",
        r"agenda|calend[aá]rio",
    ),
    Capability(
        "reports",
        "Relatórios e indicadores",
        "loadx.reports.read",
        "/reports",
        "/reports/management-summary",
        "Relatórios usam filtros e períodos do servidor e permitem exportação CSV/PDF. Verifique critérios e datas antes de comparar resultados. O LoadX não possui baseline financeiro aprovado para estimar lucro ou ROI.",
        r"relat[oó]ri\w*|indicador\w*|m[eé]tric\w*",
    ),
    Capability(
        "notifications",
        "Notificações pessoais",
        None,
        "/notifications",
        "/notifications",
        "A central mostra notificações destinadas ao usuário autenticado. É possível filtrar, marcar leitura e ajustar preferências permitidas. Nem o ADMIN ganha acesso indiscriminado às notificações pessoais de terceiros.",
        r"notifica\w*|sino",
    ),
    Capability(
        "audit",
        "Auditoria",
        "loadx.audit.read",
        "/audit",
        "/audit",
        "A auditoria consulta alterações e responsáveis com filtros e paginação do servidor. Identificadores completos e detalhes permanecem disponíveis para rastreabilidade; esta consulta não altera o histórico.",
        r"auditor\w*|hist[oó]rico de altera\w*",
    ),
    Capability(
        "integrations",
        "Integrações e saúde",
        "loadx.integrations.read",
        "/settings#settings-integrations",
        "/integration-health",
        "O painel distingue configuração e saúde observada. WhatsApp é simulado; IA real depende do provider configurado. Um componente configurado não garante conexão saudável. Tokens e credenciais não são exibidos no chat.",
        r"integra\w*|webhook|whatsapp|sa[uú]de",
        True,
    ),
    Capability(
        "events",
        "Fila de eventos",
        "loadx.settings.manage",
        "/settings#settings-outbox",
        "/outbox-events",
        "A fila permite acompanhar eventos, falhas e retentativas. Reprocessamento é administrativo e exige a ação autorizada na interface; o chat não dispara workers nem mensagens.",
        r"fila|outbox|event\w*|worker",
        True,
    ),
)


def normalize(text: str) -> str:
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", text.casefold())
            if not unicodedata.combining(c)
        ).split()
    )


def topics(message: str) -> set[str]:
    return {
        cap.key
        for cap in CAPABILITIES
        if re.search(r"\b(?:" + cap.aliases + r")\b", message, re.IGNORECASE)
    }


def permitted(user: User, capability: Capability) -> bool:
    return (
        user.active
        and (not capability.admin or user.role == "ADMIN")
        and (
            capability.permission is None or has_permission(user, capability.permission)
        )
    )


def documentation_reply(user: User, message: str) -> ChatResponse | None:
    text = normalize(message)
    general = bool(
        re.search(
            r"\b(?:como funciona o (?:sistema|loadx)|o que (?:e|faz) o loadx|quais funcionalidades|catalogo de capacidades|o que (?:voce|vc) (?:consegue |pode |sabe )?fazer(?: dentro do loadx| no loadx)?|como (?:voce|vc) pode me ajudar)\b",
            text,
        )
    )
    how = bool(
        re.search(
            r"\b(?:fale|explique|explicar|como (?:funciona|usar|uso|cadastrar|cadastro|consultar|acessar)|sobre|o que e|para que serve)\b",
            text,
        )
    )
    selected = [cap for cap in CAPABILITIES if general or cap.key in topics(message)]
    if not general and (not how or not selected):
        return None
    # Questions about *this* plan/capacity are record explanations, not documentation.
    if (
        not general
        and {cap.key for cap in selected} <= {"planning", "fleet"}
        and re.search(
            r"\b(?:esse|este|essa|esta|nao coube|rejeitad|ultimo|anterior)\b", text
        )
    ):
        return None
    visible = [cap for cap in selected if permitted(user, cap)]
    if not visible:
        return ChatResponse(
            source="GUARDRAIL",
            answer="Seu perfil não permite consultar esse módulo. Posso explicar outras funcionalidades autorizadas.",
        )
    sources = [
        Source(
            name="Como usar: " + cap.title,
            criteria="Orientação documentada, não consulta de cadastros. Fonte: docs/05-contratos-api.md; GET /api/v1"
            + cap.endpoint,
            values={"orientation": cap.guide},
        )
        for cap in visible[:18]
    ]
    if general:
        answer = (
            "O LoadX organiza cadastros, planejamento e execução logística. Para seu perfil, posso orientar: "
            + ", ".join(cap.title for cap in visible)
            + ". Sobre qual parte você quer conversar?"
        )
    else:
        answer = "\n\n".join(cap.guide for cap in visible)
    links = list(
        {
            cap.route: {"label": "Abrir " + cap.title, "href": cap.route}
            for cap in visible
        }.values()
    )[:10]
    if general:
        sources = [
            Source(
                name="Mapa de funcionalidades autorizadas",
                criteria="Documentação: docs/05-contratos-api.md e catálogo auditável do Loxi. Permissões efetivas verificadas nesta solicitação; nenhum cadastro foi consultado.",
                values={
                    "scope": "Orientação funcional; peça um módulo ou uma consulta específica."
                },
            )
        ]
        links = []
    return ChatResponse(
        source="DOCUMENTATION",
        answer=answer,
        facts=sources[:3] if general else sources,
        links=links,
    )


def scoped_request(data: ChatRequest) -> ChatRequest:
    current = topics(data.message)
    physical = bool(
        re.search(
            r"\b(?:nao coube|rejeit\w*|colis\w*|ocupacao|empilh\w*|peso|dimens\w*)\b",
            normalize(data.message),
        )
    )
    direct_reference = bool(
        re.fullmatch(
            r"(?:explique|analise|consulte|detalhe)(?: isso| esse plano| essa carga)?[?!.]*",
            normalize(data.message),
        )
    )
    planning = "planning" in current or physical or direct_reference
    related = (
        {"planning", "fleet", "loading"}
        if "planning" in current
        else {"planning", "fleet"}
    )
    unrelated = current - related
    previous_topics: set[str] = set()
    boundary = 0
    for index, message in enumerate(data.history):
        if message.role != "user":
            continue
        found = topics(message.content)
        if not found:
            continue
        if previous_topics and not previous_topics.intersection(found):
            boundary = index
        previous_topics = found
    relevant_history = data.history[boundary:]
    if current and previous_topics and not current.intersection(previous_topics):
        relevant_history = []
    if (
        re.search(r"^(?:e |mas |por que|porque|como assim)", normalize(data.message))
        and previous_topics == {"planning"}
        and not current
    ):
        planning = True
    if (
        unrelated
        or (not planning and not data.diagnostic_token)
        or (not current and previous_topics and "planning" not in previous_topics)
    ):
        return data.model_copy(
            update={
                "plan_id": None,
                "distribution_id": None,
                "diagnostic_token": None,
                "history": relevant_history,
            }
        )
    return data.model_copy(update={"history": relevant_history})
