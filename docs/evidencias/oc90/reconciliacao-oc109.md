# OC90 — reconciliação com OC109 na PR #231

`CONFIRMADO`: branch `marcelo/oc90-fluxo-multi-caminhao`; commit original
`163b59d0d6aac60cdc14aa3392cb4ef714148590` preservado. Desenvolvimento integrado:
`8f313c94ef3041aee2385d9bd2e0440b57e5360d` (PR #230 / OC109).
Integração por `git merge --no-ff origin/desenvolvimento`; sem rebase, amend,
reset, recriação da branch ou force push nesta reconciliação.

## Conflitos e revisão semântica

`CONFIRMADO`: sete conflitos resolvidos combinando as duas intenções:

- backend/migrations/README.md: head OC90 0028 após outbox OC109 0027.
- backend/tests/integration/conftest.py: roundtrips e asserts de ambas as OCs.
- backend/tests/integration/test_notification_inbox.py: backfill OC103 e limpeza
  exclusiva de fixture de teste da outbox herdada da OC109, preservados.
- docs/03-modelo-dados.md: Delivery/parte e outbox, com revisões distintas.
- docs/04-regras-negocio.md: recomposição de pedido e política de canal mantidas.
- docs/05-contratos-api.md: contratos operacionais e administração da fila mantidos.
- docs/decisions/README.md: ADR-043 outbox e ADR-044 entregas, ambas preservadas.

`CONFIRMADO`: a [revisão técnica](https://github.com/RennaN-C/loadx-smart-logistics/pull/231#pullrequestreview-5592982681)
foi lida pela conexão GitHub autorizada. Nenhuma revisão foi dispensada.

`CONFIRMADO`: outros cinco arquivos compartilhados foram revisados mesmo com
merge automático: status_history/router.py conserva LOAD_DISTRIBUTION/PART e
OUTBOX_EVENT/OUTBOX_REPROCESSED, inclusive restrição ADMIN da fila; OpenAPI conserva
as duas verificações; test_postgresql_migrations.py, test_database_readiness.py e
test_migrations_config.py usam head 0028 e cadeia 0026 → 0027 → 0028.

`CONFIRMADO`: o corpo da migration OC90 permanece idêntico ao commit original,
exceto revision/down_revision. Mantém backfill, FK, uniques, triggers de contexto,
congelamento físico, NOWAIT e downgrade fail-safe. A migration OC109
20261020_0027_outbox_events.py e ADR-043-outbox-retentativas.md ficam byte a byte
iguais a desenvolvimento. Nenhuma 0029 foi criada. ADR-044 continua proposta
implementada para revisão; nenhuma aceitação formal é inferida.

## Regressão conjunta e limites

`CONFIRMADO`: test_multi_truck_outbox.py usa optimize real, dois caminhões e
commits PostgreSQL independentes. Simula parada após commit do fato para o worker
recuperar eventos persistidos, sem depender de Session.info ou transporte real.

- A/D: um TRIP_STARTED/outbox por viagem; retry de estado não duplica fato.
  Duas pernas/comprovantes e históricos independentes; somente a última entrega
  permite Order DELIVERED; somente um histórico de início/conclusão do pedido.
- B: falhas antes e depois de inserir outbox revertem Trip/Order/históricos,
  notificação, destinatários e fila. Retry publica uma única vez.
- C: worker em transporte mock, sem transação aberta, concorre com tentativa de
  alterar snapshot de outra parte carregada. Guarda física rejeita; snapshot de
  plano/checklists/viagens/entregas/pedido/histórico é idêntico antes/depois do worker.
  As barreiras e locks de criação de loading continuam cobertos na integração.
- Migration: roundtrip OC90 com notificações OC84, recibos OC103, fila, tentativas,
  comando de reprocessamento e auditoria OC109 já persistidos conserva todas as
  linhas. Downgrade com entregas multi é recusado sem alterar fila/histórico.
  Não há exclusão de dados para fazer esse roundtrip passar.

`CONFIRMADO`: worker, fencing, lease, retentativas e reprocessamento administrativo
são os da OC109. Não houve cópia ou mudança de suas regras. A limpeza de grafo do
teste concorrente OC90 agora respeita as FKs da outbox, somente no teardown do
PostgreSQL exclusivo de teste. ADR-025/043/044 e o canal exclusivamente mock
permanecem; não há deploy ou publicação externa real.

## Reprodução e resultados novos

Em backend, com Python 3.12, dependências lock instaladas e PostgreSQL 16 exclusivo
loadx_test na porta local 55432:

```bash
python -m pytest -q tests/e2e tests/integration/test_multi_truck_operations.py tests/integration/test_multi_truck_concurrency.py tests/integration/test_operated_load_plan_snapshot.py tests/integration/test_outbox.py tests/integration/test_durable_notifications.py tests/integration/test_notification_commit_regression.py tests/integration/test_delivery_receipt_concurrency.py tests/integration/test_notification_inbox.py tests/integration/test_postgresql_migrations.py tests/integration/test_openapi.py
python -m pytest -q tests/integration tests/e2e
python -m pytest -q tests --cov=app --cov-report=term
python -m ruff check .
python -m ruff format --check .
alembic heads
alembic history
alembic check
```

Em frontend, Node 22:

```bash
npm test -- --run
npm run lint
npm run build
```

`CONFIRMADO`: quatro cenários conjuntos aprovados (20,11 s). Na rodada
exploratória inicial, 161 testes passaram e um teste novo de migration teve a
expectativa corrigida: adoção de resultado legado retorna False sem garantir
fila vazia; o teste passou a executar ciclos limitados e também validar retry
administrativo/auditoria. Não houve alteração de regras do worker por esse ajuste.
A versão final é novamente coberta pelas suítes abaixo.

`CONFIRMADO`: frontend: 944 testes/107 arquivos aprovados (73,80 s), ESLint,
TypeScript/build e bundle budget aprovados (LoadViewer 229,7 KiB gzip ≤ 250 KiB).
Nessa primeira rodada, o frontend era idêntico a desenvolvimento e o npm ci da
sessão continuava válido; a correção de dependências após o CI está descrita abaixo. Avisos AggregateError do jsdom e
chunk grande não reprovaram testes/build.

`CONFIRMADO`: Ruff check e format --check aprovados (480 arquivos).
`CONFIRMADO`: 1.318 testes de integração/E2E aprovados (192,05 s), sem falhas.
Inclui todos os arquivos focados pedidos pelo revisor, módulos operacionais,
RBAC, OpenAPI, audit, OC84/OC103/OC109, migrations e os dois E2Es multi/legado.
`CONFIRMADO`: suíte backend completa: **2.695 aprovados, zero falhas, 95% de
cobertura**, em 304,93 s. Inclui migrations/schema/metadata, quatro cenários
conjuntos, E2E multi e legado, controle de concorrência e histórico. Sete warnings:
depreciações crypt/audioop/Starlette e a fixture deliberada de identidade duplicada.
Nenhuma falha preexistente ou introduzida permanece pendente.

`CONFIRMADO`: ciclo CLI PostgreSQL 16: upgrade head, downgrade 0026, upgrade 0027,
upgrade 0028, downgrade 0027, novo upgrade 0028. Head único 20261020_0028;
history confirma 0026 → 0027 (outbox) → 0028 (Delivery/parte); alembic check sem
operações novas. Roundtrip com dados e downgrade bloqueado com pernas são
exercitados separadamente pelos testes, sem exclusão de histórico para liberar DDL.

`CONFIRMADO`: fetch final conserva desenvolvimento em 8f313c9 e remoto OC90 em
163b59d antes do commit. Auditoria de escopo/diff e ausência de marcadores,
credenciais ou artefatos inesperados aprovadas. O commit de merge `630c4fdc0b749ae3c2f91fe6328203e9684b4eec` tem como pais
essas duas referências, preservando o original e a OC109. Publicação exclusivamente
por git push normal; nunca houve force/rebase/amend/reset nesta reconciliação.

## Falha de CI herdada e correção de dependências

`CONFIRMADO`: a [execução 39526096808](https://github.com/RennaN-C/loadx-smart-logistics/actions/runs/39526096808)
do merge 630c4fd recusou Frontend em npm audit: follow-redirects 1.16.0
(GHSA-q3jh-wrc6-jgq8/GHSA-8r9p-f939-6h3c) e Vite 8.2.1
(GHSA-698v-4r3x-3vcv/GHSA-r825-w8mm-5pxw/GHSA-587h-7wmj-h5pm).
Duas vulnerabilidades high também foram reproduzidas com manifests/lock copiados
**diretamente de origin/desenvolvimento**, em diretório temporário, sem alterar a
base. Portanto são falhas preexistentes de dependências, não das regras OC90/109.

`CONFIRMADO`: correção pontual: Vite 8.2.1 → 8.2.4, mantendo major/minor e Node 22;
follow-redirects 1.16.0 → 1.16.1. Lockfile atualiza a cadeia de build compatível do
Vite (Rolldown/bindings, tipos, PostCSS/nanoid). Não há mudança em componentes,
perfis, contratos, outbox ou workflow; nenhuma exceção/ignore da auditoria. Novo
npm ci --ignore-scripts e npm audit --audit-level=high retornam zero vulnerabilidades.
A correção é outro commit normal, posterior ao merge, sem reescrita de histórico.

`CONFIRMADO`: após corrigir os pins: npm ci --ignore-scripts e npm audit aprovados
(zero vulnerabilidades), Vitest completo com 944 testes/107 arquivos aprovados
(62,59 s), ESLint, TypeScript, build e bundle budget aprovados (229,6 KiB gzip).
Backend permaneceu inalterado em relação à execução local de 2.695 testes/95%;
os workflows da publicação seguinte revalidam o SHA final completo.

## Checks e revisão

`CONFIRMADO`: a conexão GitHub autorizada permite consultar os checks. Os
resultados do SHA publicado serão entregues no relatório final para atualizar a
descrição e solicitar nova revisão. O workflow de Project não inclui synchronize;
esse push não dispara uma execução nova desse workflow, sem mudança da política.
CI/contrato da PR e Sonar são conferidos pelo SHA da publicação.

`PENDENTE DE DEFINIÇÃO`: nova revisão humana; CHANGES_REQUESTED não é dispensado
por validação local ou CI. A publicação normal atualiza a PR existente, sem criar
outra PR nem mesclar em desenvolvimento. Não há deploy.

## Inventário da PR contra desenvolvimento

`CONFIRMADO`: 46 arquivos OC90 e correção de CI contra a base integrada. Os 82 arquivos
trazidos da OC109 foram conferidos contra desenvolvimento, sem diferenças fora
dos 12 compartilhados já descritos. Componentes frontend, worker, outbox, adapter e migration/ADR
OC109 não receberam mudanças de comportamento pela reconciliação. Somente os
manifestos frontend foram atualizados para corrigir a falha herdada de CI.

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
- `backend/migrations/versions/20261020_0028_delivery_distribution_parts.py`.
- `backend/requirements-dev.lock.txt`.
- `backend/requirements-dev.txt`.
- `backend/tests/e2e/README.md`.
- `backend/tests/e2e/test_multi_truck_flow.py`.
- `backend/tests/e2e/test_multi_truck_outbox.py`.
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
- `docs/decisions/ADR-044-entregas-por-parte-distribuicao.md`.
- `docs/decisions/README.md`.
- `docs/evidencias/oc90/README.md`.
- `docs/evidencias/oc90/reconciliacao-oc109.md`.
- `frontend/package.json`.
- `frontend/package-lock.json`.
