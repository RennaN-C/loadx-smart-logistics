# Arquitetura

## Estilo

`CONFIRMADO`: o LoadX usa monólito modular com frontend separado consumindo API REST.

```text
React + TypeScript
        |
        | HTTP/JSON
        v
FastAPI modular
        |
        | SQLAlchemy
        v
PostgreSQL
```

`CONFIRMADO`: a decisão está registrada em `docs/decisions/ADR-001-monolito-modular.md`.

## Tecnologias oficiais

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings.
- Banco: PostgreSQL 16.
- Frontend: React 18, TypeScript estrito, Vite.
- HTTP frontend: Axios.
- Validação frontend: Zod quando necessário para contratos no navegador.
- Visualização: Three.js e React Three Fiber; controles oficiais do Three.js são
  importados diretamente para evitar dependências auxiliares no bundle 3D.
- Infraestrutura local: Docker Compose.
- Referência de produção: Docker Compose com Caddy como terminador TLS e servidor
  estático, conforme `ADR-021`.
- Testes: Pytest, Vitest e Testing Library.
- Integrações: IA e WhatsApp por ports/adapters, iniciando com providers mock.

`PENDENTE DE DEFINIÇÃO`: biblioteca final para relatórios PDF no frontend não está definida. No backend, `reportlab` já está listado em `backend/requirements.txt`.

## Backend

`CONFIRMADO`: cada módulo possui responsabilidade própria. Rotas chamam serviços; serviços aplicam regras; repositórios acessam o banco.

```text
router -> schemas -> service -> repository -> model
                         |
                         -> domain/optimizer
```

Para a explicação de plano, a dependência aponta para a abstração e não para
um SDK externo:

```text
load_planning router
        -> LoadPlanExplanationService
        -> AIProvider (port)
        -> FakeAIProvider no MVP / adapter concreto do Desenvolvedor 4
```

`CONFIRMADO`: o service monta um contexto técnico a partir do plano persistido e
valida a resposta do provider. A IA não acessa o banco, não chama o otimizador e
não aprova, recalcula ou modifica o plano. Timeout, indisponibilidade e resposta
inválida produzem fallback determinístico no próprio caso de uso.

Responsabilidades por pasta:

- `backend/app/main.py`: cria a aplicação FastAPI, configura CORS, registra o
  `api_router` e expõe `/health` e `/ready`.
- `backend/app/api`: agrega routers públicos da versão `/api/v1`; não implementa regra de negócio.
- `backend/app/core`: configurações globais, segurança, logging e exceções compartilhadas.
- `backend/app/database`: engine, sessão SQLAlchemy, base declarativa e utilidades de persistência.
- `backend/app/modules`: módulos de negócio do MVP.
- `backend/app/modules/<module>/models.py`: models SQLAlchemy do módulo.
- `backend/app/modules/<module>/schemas.py`: contratos Pydantic de entrada e saída.
- `backend/app/modules/<module>/repository.py`: consultas e persistência, recebendo sessão.
- `backend/app/modules/<module>/service.py`: casos de uso e regras de negócio.
- `backend/app/modules/<module>/router.py`: endpoints HTTP do módulo.
- `backend/app/modules/<module>/domain`: regras puras, algoritmos e objetos sem dependência de FastAPI ou banco.
- `backend/app/integrations`: adapters para IA, WhatsApp e futuros provedores externos.
- `backend/app/shared`: tipos, erros e utilitários usados por mais de um módulo.
- `backend/migrations`: migrations Alembic.
- `backend/tests`: testes unitários, integração e e2e.

`CONFIRMADO`: no estado atual do código, existem base FastAPI, configurações,
sessão SQLAlchemy, liveness, readiness com PostgreSQL/Alembic, migrations e
módulos backend para autenticação, usuários, caminhões, produtos, clientes,
motoristas, pedidos e histórico de status.

`CONFIRMADO`: o planejamento de carga está implementado até a `OC22`, com
persistência dos planos, API protegida e engine determinística. A `OC21` compara
transitoriamente de 2 a 10 caminhões sem criar `LoadPlan`; a `OC22` explica um
plano persistido por `AIProvider` ou fallback determinístico. A `OC51` aplica a
matriz de permissões em todas as rotas atuais.

`CONFIRMADO`: carregamento, viagens, entregas, ocorrências, notificações mock e
relatórios possuem módulos backend integrados para o fluxo da v1.0.0.

## Frontend

`CONFIRMADO`: organização por funcionalidades visíveis do produto.

Responsabilidades por pasta:

- `frontend/src/app`: inicialização React, providers globais, layout e rotas.
- `frontend/src/components`: componentes realmente compartilhados por mais de uma feature.
- `frontend/src/features`: telas e comportamento por domínio.
- `frontend/src/features/<feature>/pages`: telas da feature.
- `frontend/src/features/<feature>/components`: componentes usados somente pela feature.
- `frontend/src/features/<feature>/api`: chamadas HTTP da feature.
- `frontend/src/features/<feature>/hooks`: estado e comportamento reutilizável da feature.
- `frontend/src/features/<feature>/types.ts`: tipos locais.
- `frontend/src/services`: cliente HTTP, tratamento padronizado de erros e adapters do navegador.
- `frontend/src/types`: tipos globais mínimos, como erro padrão de API ou paginação.
- `frontend/src/tests`: configuração e testes de integração visual.

`CONFIRMADO`: o frontend exibe o plano calculado. Ele não decide validade física nem recalcula posições.

## Infraestrutura

- `compose.yaml`: sobe PostgreSQL, aplica migrations em serviço one-shot e então
  inicia backend e frontend para desenvolvimento local.
- `infra/database`: instruções complementares de banco e seeds.
- `infra/scripts`: scripts auxiliares idempotentes quando possível.
- `infra/ci`: documentação do pipeline futuro.
- `.env.example`: contrato de variáveis esperadas, sem segredos reais.

## Dependências permitidas

- Módulos podem consumir serviços públicos de outros módulos.
- O módulo de planejamento pode consultar caminhões, produtos e pedidos por services públicos.
- A visualização 3D consome somente o resultado aprovado ou calculado pela API.
- Integrações externas chamam services públicos e não acessam o banco diretamente.
- Regras puras podem ficar em `domain/` e serem testadas sem FastAPI, banco ou rede.
- O caso de uso de explicação depende somente da port `AIProvider`; o adapter
  concreto e suas credenciais pertencem ao Desenvolvedor 4.

## Dependências proibidas

- Frontend calculando validade geométrica.
- IA decidindo se uma solução física é válida.
- IA recebendo dados pessoais de cliente, motorista, telefone, documento ou
  endereço para explicar um plano.
- Rotas HTTP contendo regras complexas.
- Services com SQL direto.
- Repositories chamando FastAPI ou integrações externas.
- Um módulo alterando diretamente modelos internos de outro módulo.
- Integrações externas acessando tabelas diretamente.

## Erros, logs e segurança

- `CONFIRMADO`: o formato de erro público está documentado em `docs/05-contratos-api.md`.
- `RECOMENDAÇÃO`: exceções de domínio devem ser traduzidas para respostas HTTP no router ou handler compartilhado, preservando código estável de erro.
- `RECOMENDAÇÃO`: logs devem registrar eventos técnicos e IDs de entidade, mas não senha, token, documento pessoal completo, payload sensível ou segredo.
- `CONFIRMADO`: CORS vem de `BACKEND_CORS_ORIGINS`.
- `CONFIRMADO`: `SECRET_KEY`, tokens de IA e WhatsApp vêm de `.env`.
- `CONFIRMADO`: conforme `ADR-019` e `ADR-020`, produção falha ao iniciar com
  segredo fraco, URL local padrão ou CORS curinga. `SECRET_KEY` protege HMACs de
  autenticação; JWT não integra mais o contrato.
- `CONFIRMADO`: os containers de aplicação e migration usam usuário sem
  privilégio, capabilities removidas e `no-new-privileges`; portas locais ficam
  vinculadas a `127.0.0.1`.
- `CONFIRMADO`: `APP_ENV` aceita `local` ou `production`; a documentação HTTP da API é registrada somente em `local` e o valor padrão seguro é `production`.
- `CONFIRMADO`: a fronteira de endpoints, a matriz RBAC e o bootstrap administrativo seguem `ADR-004`.
- `CONFIRMADO`: D11 e `ADR-018` mantêm `/health` como liveness e definem
  `/ready` como verificação pública e genérica de PostgreSQL e Alembic.
- `CONFIRMADO`: D18 e `ADR-020` definem sessão opaca revogável, cookie seguro,
  CSRF, throttling de login, Argon2id e política de senha.
- `CONFIRMADO`: a API desabilita cache de respostas, framing, MIME sniffing,
  referrer e permissões desnecessárias; a CSP da API nega recursos por padrão e
  HSTS é emitido quando `APP_ENV=production`.
- `PENDENTE DE DEFINIÇÃO`: recuperação de senha e MFA possuem ocorrências futuras
  próprias.
