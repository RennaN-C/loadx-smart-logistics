# Padrões de desenvolvimento

## Git

Branches:

- `main`: versão estável.
- `desenvolvimento`: integração.
- `Branch Pessoal`: Cada desenvolvedor terá sua branch pessoal depois sera feito merge com a branch "desenvolvimento" e a cada módulo completo será feito merge com a "main"
- `feature/OCXX-descricao`: uma ocorrência de funcionalidade.
- `fix/OCXX-descricao`: correção vinculada a ocorrência ou bug.
- `docs/OCXX-descricao`: documentação vinculada a ocorrência.

Commits:

- `feat: ...`.
- `fix: ...`.
- `test: ...`.
- `docs: ...`.
- `refactor: ...`.
- `chore: ...`.

`RECOMENDAÇÃO`: incluir a ocorrência no corpo do commit ou no título do PR, por exemplo `OC15`.

## Pull Request

Toda alteração entra por Pull Request para `desenvolvimento`. Exigir pelo menos uma revisão.

Checklist mínimo:

- Está dentro do escopo do MVP.
- Tem ocorrência aprovada.
- Não contém segredos ou dados reais.
- Testes foram criados ou atualizados.
- Migrations foram incluídas quando necessárias.
- Contratos e documentação foram atualizados.
- Outro integrante revisou a mudança.

## Processo para criar uma funcionalidade

1. Abrir ou confirmar a ocorrência `OCXX`.
2. Ler `AGENTS.md`, docs relacionados e README da pasta.
3. Identificar módulo dono e contratos afetados.
4. Atualizar documentação primeiro quando houver mudança de regra, banco, arquitetura ou API.
5. Implementar a menor parte coerente da ocorrência.
6. Adicionar testes mínimos.
7. Rodar validações locais.
8. Abrir PR com resumo, testes e pendências.

## Padrões gerais de nomes

- Código, tabelas, rotas, campos e arquivos técnicos em inglês.
- Interface e documentação podem ficar em português.
- Variáveis e funções em `snake_case` no Python.
- Variáveis e funções em `camelCase` no TypeScript.
- Classes em `PascalCase`.
- Constantes em `UPPER_SNAKE_CASE`.
- Arquivos Python em `snake_case.py`.
- Arquivos React component em `PascalCase.tsx`.
- Hooks React começam com `use`, como `useLoadPlan`.
- Testes citam o comportamento esperado no nome.

Exemplos adaptados do projeto:

- `internal_width_cm`, `max_weight_kg`, `expected_delivery_at`.
- `load_planning`, `load_plan_items`, `loading_sequence`.
- `api_router`, `SessionLocal`, `Settings`.
- `App.tsx`, `api.ts`, `styles.css`.

## Backend

Padrão por módulo:

- `models.py`: entidades SQLAlchemy do módulo.
- `schemas.py`: contratos Pydantic.
- `repository.py`: consultas e persistência.
- `service.py`: regras e casos de uso.
- `router.py`: endpoints HTTP.
- `domain/`: regras puras e algoritmos sem FastAPI ou banco.

Regras:

- Rotas validam entrada, chamam service e formatam resposta.
- Services não devem conter SQL direto.
- Repositories recebem sessão SQLAlchemy.
- Models não devem conter regra de negócio complexa.
- Domain não acessa banco, HTTP, FastAPI ou integrações externas.
- Configurações vêm de `app/core/config.py` e `.env`.
- Use type hints em funções públicas.
- Use Pydantic para entrada e saída de API.

Exemplo de nomes por módulo:

- Model: `Truck`.
- Schema de criação: `TruckCreate`.
- Schema de atualização: `TruckUpdate`.
- Schema de resposta: `TruckRead`.
- Repository: `TruckRepository`.
- Service: `TruckService`.
- Router: `router`.

`RECOMENDAÇÃO`: services devem expor métodos com verbos claros, como `create_truck`, `approve_load_plan` e `register_occurrence`.

## Frontend

Padrão por feature:

- `pages/`: telas roteáveis da feature.
- `components/`: componentes locais.
- `api/`: chamadas HTTP da feature.
- `hooks/`: estado e comportamento reutilizável.
- `types.ts`: tipos locais.

Regras:

- TypeScript estrito.
- Não espalhar chamadas Axios diretamente pelas páginas.
- Usar `frontend/src/services/api.ts` como cliente HTTP base.
- Tratar estados de loading, vazio e erro.
- Componentes compartilhados ficam em `src/components` apenas quando usados por mais de uma feature.
- Tipos globais ficam em `src/types` apenas quando usados por várias features.
- A cena 3D usa exclusivamente coordenadas da API.
- O frontend pode validar formulário, mas não valida regra física crítica.

Exemplo de nomes:

- `TruckListPage.tsx`.
- `TruckForm.tsx`.
- `useTrucks.ts`.
- `trucksApi.ts`.
- `TruckSummary`.

## Banco

- Cada pessoa usa PostgreSQL local.
- Staging é compartilhado apenas para integração.
- Alterações estruturais somente por Alembic.
- Nunca editar a estrutura oficial apenas pelo pgAdmin.
- Seeds devem usar dados fictícios.
- Tabelas em plural snake_case.
- Colunas em snake_case.
- Chaves estrangeiras com sufixo `_id`.
- Dimensões com sufixo `_cm`.
- Pesos com sufixo `_kg`.
- Datas em UTC com sufixo `_at`.

Antes de criar migration:

1. Conferir `docs/03-modelo-dados.md`.
2. Atualizar `docs/03` se houver tabela, coluna, índice ou constraint nova.
3. Criar ou atualizar model SQLAlchemy no módulo dono.
4. Gerar migration Alembic.
5. Revisar upgrade/downgrade.
6. Adicionar teste mínimo.

## Docker

- `CONFIRMADO`: os contextos de build de `backend` e `frontend` mantêm
  `.dockerignore` próprios para não enviar ambientes virtuais, `node_modules`,
  caches, cobertura ou artefatos de build ao daemon.
- `CONFIRMADO`: a imagem do frontend usa `npm ci` e o `package-lock.json` para
  instalar exatamente a árvore de dependências versionada.
- `CONFIRMADO`: a imagem do backend normaliza arquivos Python como não
  executáveis para preservar o mesmo resultado do Ruff quando o contexto vem do
  Docker Desktop no Windows.
- `CONFIRMADO`: o serviço one-shot `migrate` aplica `alembic upgrade head` após
  o PostgreSQL ficar saudável; o backend depende de sua conclusão e seu
  healthcheck consome `/ready`.
- `CONFIRMADO`: `/ready` continua somente leitura. Automatizar a migration no
  Compose não transfere essa responsabilidade para o endpoint.
- `CONFIRMADO`: backend, migration e frontend executam sem root, sem capabilities
  Linux e com `no-new-privileges`; portas publicadas ficam em loopback por padrão.

## Endpoints

- Prefixo de negócio: `/api/v1`.
- Liveness: `/health`.
- Readiness: `/ready`, com PostgreSQL acessível e Alembic exatamente no head.
- Caminhos em kebab-case.
- Recursos no plural: `/trucks`, `/load-plans`, `/loading-sessions`.
- IDs no path: `/{id}`.
- Ações explícitas por verbo quando não forem CRUD simples: `/load-plans/{id}/approve`.
- Payloads e respostas em snake_case.
- Erros no formato de `docs/05-contratos-api.md`.

`CONFIRMADO` por D11 e `ADR-018`: readiness é somente leitura, possui orçamento
total de 2 segundos e retorna falha genérica sem detalhes de infraestrutura.

## Erros e logs

- Códigos de erro em `UPPER_SNAKE_CASE`.
- Mensagens de erro em português podem ser exibidas ao usuário.
- `details` deve trazer campos, IDs ou motivos quando ajudar correção.
- Não logar senha, token, segredo, documento pessoal completo ou foto.
- Logs devem incluir contexto técnico suficiente, como módulo, ação e ID da entidade.
- Erros de domínio devem ser testáveis sem FastAPI quando possível.

`PENDENTE DE DEFINIÇÃO`: biblioteca/configuração final de logging estruturado.

## Segurança

- Segredos ficam em `.env`, nunca no código.
- `.env.example` documenta variáveis sem valores reais sensíveis.
- Senhas devem ser armazenadas como hash.
- Respostas de API nunca retornam `password_hash`.
- Integrações externas devem usar adapters e providers mock no desenvolvimento inicial.
- Dados pessoais reais não entram em seeds, testes, exemplos ou prints de documentação.

`PENDENTE DE DEFINIÇÃO`: política final de RBAC por endpoint.

## Testes

Backend:

- Unitários em `backend/tests/unit`.
- Integração em `backend/tests/integration`.
- E2E em `backend/tests/e2e`.
- Health check atual em `backend/tests/test_health.py`.
- Regras puras e otimizador devem ter testes unitários sem banco externo.
- Rotas, repositories e migrations usam PostgreSQL 16 exclusivo nos testes de
  integração, com estrutura criada por `alembic upgrade head`, nunca por
  `Base.metadata.create_all`.
- A URL de integração vem somente de `TEST_DATABASE_URL`, deve apontar para
  `loadx_test` e nunca pode reutilizar desenvolvimento, staging ou produção.
- O ambiente e os comandos locais estão em `backend/tests/README.md` e
  `backend/tests/integration/README.md`.

Frontend:

- Testes com Vitest e Testing Library.
- Simular API para manter testes independentes.
- Testar loading, vazio, erro e validações de formulário.
- Testar transformação de coordenadas para a cena 3D sem depender do backend real.

Nomes de testes:

- Python: `test_<comportamento>_<resultado>()`.
- TypeScript: `<Component>.test.tsx` ou `<feature>.test.ts`.

Exemplos:

- `test_rejects_volume_outside_truck_limits`.
- `test_prevents_weight_above_truck_capacity`.
- `LoadPlanVisualization.test.tsx`.

## Definição de pronto

Uma ocorrência está pronta quando:

- critérios de aceite atendidos;
- código revisado;
- testes passando;
- migration incluída, quando necessária;
- documentação atualizada;
- integração verificada;
- riscos ou pendências reportados.

## Padrão de qualidade

- Python formatado e validado com Ruff.
- TypeScript validado por ESLint.
- Funções curtas e nomes claros.
- Regras críticas com testes unitários.
- Erros de API no formato documentado.
- Mudanças pequenas e focadas.

`PENDENTE DE DEFINIÇÃO`: comandos oficiais de lint/test/build em CI ainda não estão implementados em pipeline.
