# Assistente LoadX — Issue #336

Chat consultivo opt-in, com provider Groq no backend e registro fechado de
ferramentas read-only. ADR-048 registra arquitetura, métricas, permissões e limites.
Nenhum comando de escrita, SQL livre, hospedagem de modelo ou tenant é criado.

## API

`POST /api/v1/assistant/messages`: `message` (1–2.000 caracteres), até 8 mensagens
`history` (`user`/`assistant`, 2.000 caracteres cada), `plan_id`/`distribution_id`
opcionais; customer_id é uma seleção explícita, revalidada apenas por ferramentas
autorizadas de cliente. Contexto e vínculos são verificados contra serviços existentes.
Resposta: `source=GROQ|FALLBACK`, `answer`, fatos/critério/período UTC, sugestões e
links internos montados no servidor. Sessão, Origin e CSRF obrigatórios.
ADMIN/LOGISTICS_MANAGER/CHECKER; DRIVER/CUSTOM negados. Cada ferramenta verifica
permissões efetivas. CHECKER recebe apenas contexto aprovado e disponibilidade
operacional paginada, não métricas globais de clientes/negócio.
401/403/404/422/429 usam envelope padrão. Falha de IA gera FALLBACK sem esconder
falha de autorização. Requisições não alteram estado operacional.

## Ferramentas

- `get_company_summary`: nome institucional, somente ADMIN.
- `get_customer_order_metrics`: criação e situação atual de pedidos; cliente opcional.
- `get_delivery_metrics`: expedição por viagem iniciada; pedidos integralmente
  entregues por última perna; pernas concluídas e cliente líder são distintos.
- `get_fleet_utilization`: viagens, caminhões distintos e ocupação média aritmética
  por plano de viagens iniciadas; snapshots planejados, sem lucro/ROI.
- `get_fleet_availability`: 20 veículos por página, disponibilidade atual oficial;
  não apresenta coleção parcial como agregado global.
- `get_canceled_distributions`: atualmente canceladas e criadas no período,
  sem inventar timestamp de cancelamento.
- `get_financial_impact`: apenas insuficiência de receita/custo/baseline, ADMIN;
  nenhum acesso financeiro real nem percentual inferido.

Período padrão: 30 dias UTC, máximo 93, início inclusivo/fim exclusivo. Cliente
normalizado com equivalência de caixa/acentos; correspondência exata tem prioridade.
Nomes ambíguos oferecem seleção explícita (nome/cidade/UF/documento mascarado).
A referência é revalidada e o filtro fica visível e registrado nos fatos. Opções,
referências e rótulo do filtro não são enviados ao provider. Não há escolha automática.
Consultas agregadas parametrizadas pertencem ao módulo reports; nenhuma migration.

## Configuração (Render ou processo backend)

- `AI_PROVIDER=groq`
- `GROQ_API_KEY`: segredo exclusivo do backend, nunca VITE_ ou browser.
- `GROQ_MODEL`: identificador disponível/aprovado na conta Groq; padrão configurável
  `llama-3.3-70b-versatile`, sem afirmar disponibilidade na conta sem chamada real.
- `AI_CHAT_TIMEOUT_SECONDS=10` (1–20); `AI_CHAT_REQUESTS_PER_MINUTE=6` (1–30).
- `AI_EXPLANATION_TIMEOUT_SECONDS=5` preserva a API legada de explicação.

Sem configuração ou em erro: fallback identificado. O modo `mock` não é rotulado
como IA real no runtime. Não instalar SDK ou adicionar segredos ao frontend.
Compose local já usa .env privado. Produção pode fornecer GROQ_API_KEY pelo
mecanismo existente de secrets/Settings; nenhum serviço externo foi configurado.
Vercel continua usando somente a API do backend, sem chave ou novo serviço.
Saúde Groq configurada é LIMITED, não comprova conectividade/disponibilidade real.

## Segurança e limites

Até 2 chamadas e 3 ferramentas por pergunta. Endpoint Groq fixo HTTPS, sem
redirects/retry automático, corpo de entrada/saída limitado a 64 KiB, saída até
8.000 caracteres/700 tokens. Perguntas são redigidas para contatos/documentos,
UUIDs, URLs e padrões de segredos; o filtro não substitui política de não enviar
PII em texto livre. Resultados minimizados; números reais ficam inspecionáveis.

Histórico não é fonte de autoridade e é volátil, separado por identidade/perfil
na UI. Advisory lock PostgreSQL impede simultaneidade do mesmo ator; budget de
minuto é por processo e multiplica por workers. Não reutiliza throttle de login.
Consultas registram evento de segurança com ator/ferramenta, sem texto, filtros,
resultados ou segredos; retenção depende do coletor existente.

Testes HTTP simulados do provider não são prova de integração Groq ao vivo.
Configuração, aceite de dados e teste real pertencem ao responsável; esta PR não
executa deploy, altera contas ou envia mensagens a serviços externos.

### Docker Compose e fronteira de segredo

O serviço frontend local não recebe mais o .env compartilhado: só usa as
variáveis públicas explícitas já definidas (API/proxy). Isso impede que a chave
Groq ou outros segredos backend entrem no ambiente do container frontend.
Na referência de produção, o override opcional `compose.groq.yaml` mantém a chave
em secret `/run/secrets/GROQ_API_KEY` exclusivamente no backend. Com a configuração
segura do ambiente já preparada pelo operador, combinar
`compose.production.yaml` + `compose.groq.yaml`; não usar o override em frontend
nem copiar a chave para VITE_. Nenhum compose up/deploy de produção foi executado.
