# OC90 — validação operacional e integridade

`CONFIRMADO`: implementação da Issue #133 em
`marcelo/oc90-fluxo-multi-caminhao`, baseada em
`41e00bd0690070c0965b75b2fdb0fbd46d5e9d68` de desenvolvimento. Validação local
em 20/10/2026, Python 3.12, PostgreSQL 16 exclusivo `loadx_test` e Node 22.23.1.
Dados fictícios; sem serviços externos reais, deploy, PR ou alteração da Issue.

## Cenários verificados

- Optimize real força exatamente dois caminhões para dois volumes não
  rotacionáveis/não empilháveis. Identidades originais permanecem disjuntas.
- Aprovação total libera somente planos atuais/partes aprovadas. Reprocessados
  antigos permanecem bloqueados, inclusive no início de sessão obsoleta.
- Loadings/checklists independentes; create repetido não duplica itens/sessões.
- Duas Trips/entregas por partes, com conflito estável para Trip duplicada.
  Falha de B por loading incompleto não modifica A; retry continua após finalizar B.
- Primeiro início gera uma transição Order; primeira entrega não conclui o pedido;
  primeira Trip pode terminar. Última perna necessária conclui o pedido uma vez.
  Cenário de três partes comprova agregação somente do subconjunto do pedido.
- Duas conclusões concorrentes em transações PostgreSQL independentes e com
  identity maps obsoletos produzem dois comprovantes distintos e um histórico
  final do pedido. Repetições conservam os mesmos comprovantes/históricos.
- Falha de auditoria faz rollback integral da criação/conclusão de uma perna.
- Permissões fixas, vínculo de motorista e grant CUSTOM de deliveries.manage
  preservados; CUSTOM não herda leitura/gestão de viagem nem poderes de gerente.
- Escrita direta inválida: duplicação parte/pedido e legado, parte inexistente,
  parte de outra distribuição, pedido válido sem volume, plano incompatível,
  reatribuição de contexto e alterações dos pais operacionais são recusadas.
- Migration 0027: upgrade/downgrade/novo upgrade real, backfill de entrega OC87,
  preservação de legado/histórico, recusa de downgrade com pernas e rollback de
  upgrade sobre vínculo antigo inconsistente. Head único e metadata em acordo.
- PDFs reais das duas partes/viagens são extraídos com pypdf (apenas em testes)
  e identificam distribuição, parte, plano, caminhão, quantidade e identidades
  físicas. Auditoria existente permite reconstruir vínculos e transições.
- Fluxo E2E legado permanece sem alterações no arquivo test_complete_flow.py.
  Nenhum endpoint, evento operacional, regra física ou status de pedido novo.

## Reprodução

Na raiz, disponibilizar o PostgreSQL exclusivo com o Compose de teste publicado.
Em backend, exportar TEST_DATABASE_URL conforme tests/integration/README.md e
usar ambiente Python com requirements-dev.lock.txt instalado com --require-hashes.

```bash
python -m pytest -q tests/integration/test_multi_truck_operations.py tests/integration/test_multi_truck_concurrency.py tests/integration/test_operated_load_plan_snapshot.py tests/e2e/test_multi_truck_flow.py tests/integration/test_openapi.py tests/integration/test_delivery_receipts_api.py tests/unit/test_database_readiness.py
python -m pytest -q tests --cov=app --cov-report=term
python -m ruff check .
python -m ruff format --check .
alembic heads
```

Em frontend, com Node 22 e npm ci:

```bash
npm test -- --run
npm run lint
npm run build
```

`CONFIRMADO`: nenhuma alteração de frontend foi necessária; o campo opcional
na resposta de Delivery é aditivo. Build inclui TypeScript e bundle budget.
A instalação Python com hashes foi validada, preservando todos os pins anteriores.

## Limites e revisão

`PENDENTE DE DEFINIÇÃO`: aceite formal da [ADR-043](../../decisions/ADR-043-entregas-por-parte-distribuicao.md)
pela equipe. A UI OC89 incorporada à base não é alterada pela OC90; exceções/cancelamento/reentrega OC94 permanecem fora do escopo.
Downgrade com qualquer entrega de parte exige migration compensatória; remover
histórico para contornar a guarda não é permitido. Observabilidade ADR-025
mantém a allowlist; reconstrução durável usa banco/StatusHistory, sem IDs/PII
adicionais em logs. Testes locais não representam homologação ou deploy produtivo.


## Correção final de integridade

`CONFIRMADO`: desenvolvimento avançou desde a revisão remota `94dcfe7`.
A branch foi rebaseada sobre a base registrada acima, preservando OC83/OC84,
OC89 e OC103. As revisões 0025/0026 e ADRs 041/042 já pertencem a notificações
nessa base; a mesma migration OC90 e sua proposta ADR foram renumeradas para
0027 e ADR-043. Continua existindo apenas uma migration e um commit OC90.
O teste de backfill OC103 aponta explicitamente ao seu pai 0025, em vez de
presumir que a revisão anterior ao head ainda é OC103. A limpeza do teste
concorrente preserva as FKs das notificações presentes na nova base.

`CONFIRMADO`: LoadingSession persistida marca o congelamento de linhas inteiras
de LoadPlan, LoadPlanOrder e LoadPlanItem. Trip é evidência defensiva adicional,
mesmo sem loading; o legado recebe a mesma proteção. Três triggers compartilham
`protect_operated_load_plan()` e a constraint estável
`ck_load_plans__operational_snapshot` (SQLSTATE 23514). UPDATE no-op é permitido;
downgrade permitido remove todos os triggers/função, enquanto entregas com parte
continuam bloqueando downgrade antes de qualquer DDL.

`CONFIRMADO`: criação de loading toma LoadPlan FOR UPDATE antes de ler itens e
bloquear caminhão. O repository atualiza o identity map após adquirir o lock.
A guarda de escrita direta testa pais antigos/novos em UUID crescente e usa
NOWAIT: um filho já bloqueado não espera por um pai que esteja criando FK do
checklist nele. Contenção exige rollback/retry da transação, mesmo antes da
operação. A guarda apenas consulta LoadingSession/Trip, sem tomar locks nelas,
em distribuição ou pedido. Trip create e os locks existentes de contexto e
partição continuam intactos. Testes com transações reais exercitam ambos os
sentidos: loading primeiro/DELETE de item concorrente e mutação primeiro/leituras
obsoletas na criação do loading.

`CONFIRMADO`: 51 casos de escrita direta cobrem caminhão, snapshot de caminhão,
métricas, algoritmo, exclusão/identidade do plano, posição, sequência, snapshot
do produto, rotação/dimensões coerentes, inserção/exclusão/reatribuição de itens
e pedidos, nos cenários multi com loading, legado com loading e legado com Trip.
Todos verificam o nome da nova constraint. Também são testados no-op nas três
tabelas, reatribuição de filho não operado para pai operado, criação/reprocessamento/
aprovação antes da operação e remoção/restauração das guardas no downgrade/upgrade.
Não há nova tabela, campo HTTP, status ou mudança de algoritmo.

## Resultados finais

`CONFIRMADO`: rodada focada inicial: 87 testes aprovados (56,77 s).
Inclui operações multi, guardas físicas, concorrência e migrations locais.
Regressão ampliada: 1.294 testes aprovados (173,86 s), incluindo toda a suíte
de integração, E2Es multi/legado, OpenAPI, relatórios, receipts e migrations.
Suíte backend completa: 2.620 testes aprovados, zero falhas e 95% de cobertura
(279,44 s). Inclui a versão final dos testes concorrentes com caminhão e
sequência dos itens previamente carregados no identity map.

`CONFIRMADO`: Ruff check e Ruff format --check aprovados (467 arquivos).
Ciclo CLI explícito: upgrade head → downgrade 0026 → upgrade head, head único
20261020_0027 e alembic check sem operações novas. Metadata/schema e fail-safe
de downgrade também aprovados na suíte PostgreSQL. Os sete warnings da suíte
completa são depreciações crypt/audioop/Starlette e a fixture deliberada de
identidade duplicada; nenhuma falha introduzida ou preexistente ficou pendente.

`CONFIRMADO`: frontend completo reexecutado sobre a nova base: 925 testes em
105 arquivos aprovados. ESLint, TypeScript, build e bundle budget aprovados;
LoadViewer 229,7 KiB gzip, limite 250 KiB. Aviso do bundler sobre chunk grande e
mensagens AggregateError do jsdom não reprovaram testes/build.
Nenhum arquivo frontend foi alterado pela OC90.

`CONFIRMADO`: auditoria de escopo e git diff --check aprovados. O novo fetch
conserva desenvolvimento em 41e00bd e a branch remota no commit esperado 94dcfe7
antes da publicação. A OC90 permanece um commit sobre desenvolvimento (+1/-0),
com publicação protegida por lease explícita contra esse SHA remoto. Não há
arquivos de frontend, logs, cobertura, dumps, .env ou artefatos de build no diff.
Issue #133 não é alterada; sem PR ou merge.

## Arquivos desta correção

`CONFIRMADO`: 17 arquivos de proteção física, testes e documentação:

- `backend/app/modules/deliveries/README.md`.
- `backend/app/modules/load_planning/README.md`.
- `backend/app/modules/load_planning/distributions.md`.
- `backend/app/modules/load_planning/repository.py`.
- `backend/app/modules/loading/README.md`.
- `backend/app/modules/loading/service.py`.
- `backend/migrations/README.md`.
- `backend/migrations/versions/20261020_0027_delivery_distribution_parts.py`.
- `backend/tests/integration/test_multi_truck_concurrency.py`.
- `backend/tests/integration/test_multi_truck_operations.py`.
- `backend/tests/integration/test_notification_inbox.py`.
- `backend/tests/integration/test_operated_load_plan_snapshot.py`.
- `docs/03-modelo-dados.md`.
- `docs/04-regras-negocio.md`.
- `docs/decisions/ADR-043-entregas-por-parte-distribuicao.md`.
- `docs/decisions/README.md`.
- `docs/evidencias/oc90/README.md`.

A atualização da base também ajusta quatro testes/fixtures para o novo head:

- `backend/tests/integration/conftest.py`.
- `backend/tests/integration/test_postgresql_migrations.py`.
- `backend/tests/unit/test_database_readiness.py`.
- `backend/tests/unit/test_migrations_config.py`.

## Inventário do diff

`CONFIRMADO`: 42 arquivos pertencem à OC90 sobre a base atual:

- `backend/app/modules/deliveries/README.md`.
- `backend/app/modules/deliveries/models.py`.
- `backend/app/modules/deliveries/repository.py`.
- `backend/app/modules/deliveries/schemas.py`.
- `backend/app/modules/deliveries/service.py`.
- `backend/app/modules/load_planning/README.md`.
- `backend/app/modules/load_planning/distribution_repository.py`.
- `backend/app/modules/load_planning/distributions.md`.
- `backend/app/modules/load_planning/reference_service.py`.
- `backend/app/modules/load_planning/repository.py`.
- `backend/app/modules/loading/README.md`.
- `backend/app/modules/loading/router.py`.
- `backend/app/modules/loading/service.py`.
- `backend/app/modules/reports/README.md`.
- `backend/app/modules/reports/service.py`.
- `backend/app/modules/status_history/README.md`.
- `backend/app/modules/status_history/router.py`.
- `backend/migrations/README.md`.
- `backend/migrations/versions/20261020_0027_delivery_distribution_parts.py`.
- `backend/requirements-dev.lock.txt`.
- `backend/requirements-dev.txt`.
- `backend/tests/e2e/README.md`.
- `backend/tests/e2e/test_multi_truck_flow.py`.
- `backend/tests/integration/conftest.py`.
- `backend/tests/integration/oc90_helpers.py`.
- `backend/tests/integration/test_delivery_receipts_api.py`.
- `backend/tests/integration/test_load_distributions.py`.
- `backend/tests/integration/test_multi_truck_concurrency.py`.
- `backend/tests/integration/test_multi_truck_operations.py`.
- `backend/tests/integration/test_notification_inbox.py`.
- `backend/tests/integration/test_openapi.py`.
- `backend/tests/integration/test_operated_load_plan_snapshot.py`.
- `backend/tests/integration/test_postgresql_migrations.py`.
- `backend/tests/unit/test_database_readiness.py`.
- `backend/tests/unit/test_delivery_models.py`.
- `backend/tests/unit/test_migrations_config.py`.
- `docs/03-modelo-dados.md`.
- `docs/04-regras-negocio.md`.
- `docs/05-contratos-api.md`.
- `docs/decisions/ADR-043-entregas-por-parte-distribuicao.md`.
- `docs/decisions/README.md`.
- `docs/evidencias/oc90/README.md`.
