# Issue #430 — integração de desenvolvimento e revalidação

`CONFIRMADO`: integração solicitada após auditoria técnica das otimizações,
em 15/11/2026. Branch `joao/expandir-capacidade-otimizador`, Identificador N/A.

## Histórico preservado

| Referência | SHA |
| --- | --- |
| Base original dos benchmarks | `cb9c6f7d7f0e1b2829cae938a15e2fc63d6be09e` |
| Entrega original da Issue #430 | `c366fb9ec5455c2a29a5ab2876786528e8f9be2f` |
| Desenvolvimento recebido por fetch | `4cf4e9236dcbf89f0511d365fd096d2ef8d6cc5b` |
| Merge normal validado | `81be69efee72f974bf5b96874506902dd9426bcf` |

`CONFIRMADO`: worktree inicialmente limpa; HEAD local e remoto iguais a c366fb9e.
O clone busca somente main por padrão, portanto após `git fetch origin --prune`
foram buscadas explicitamente as referências de desenvolvimento e desta branch.
Merge com `--no-ff`, sem conflitos, usando ort. Pais: c366fb9e e 4cf4e923.
Nenhum commit publicado foi reescrito. O commit posterior deste registro altera
somente documentação, sem mudar o código executado nos testes.

## Compatibilidade e limites

`CONFIRMADO`: o avanço recebido é o isolamento G03-B2 dos tipos documentais de
motoristas por organização (#479). CNH nativa permanece global; tipos adicionais
recebem owner, unicidade por organização e FKs compostas de documentos/políticas.
Repository/service e testes recebidos foram preservados integralmente, sem
adaptação dos constraints ou do isolamento para permitir a integração.

`CONFIRMADO`: optimizer, benchmarks, snapshots de referência e evidências RAW
são idênticos aos de c366fb9e. SHA-256 dos arquivos Python do optimizer:
`e9e2bb178419128c3066d107ec14d49d2eefb39fc8bfd802e3b4e2b377c6b4cf`.
O índice espacial, a otimização da profundidade, os apoios e a revalidação final
permanecem. `heuristic-v1`, MAX_VOLUMES=200, dez partes e fronteira de 64 estados
foram conferidos diretamente. Schemas mantêm maxItems=200 nas seleções/volumes
da distribuição e maxItems=10 nas partes/candidatos da comparação.

`CONFIRMADO`: consolidador reexecutado: **117 resultados completos comparados,
zero divergências**. JSON de comparação e CSV continuam byte a byte iguais aos
publicados. A suíte focada também executa novamente os snapshots, determinismo,
oráculos físicos e isolamento concorrente. Nenhum benchmark pesado foi repetido;
tempos anteriores não foram substituídos por estimativas nem apresentados como
medições novas do serviço combinado.

## Alembic e PostgreSQL

`CONFIRMADO`: `python -m alembic heads` informa head único
`20261115_0041`, com down_revision `20261115_0040`. A revisão 0041 foi recebida
de desenvolvimento sem alterações; nenhuma nova migration foi criada aqui.
Testes de configuração/readiness confirmam o head e sua cadeia. A regressão
completa usa somente PostgreSQL 16 exclusivo `loadx_test`, com migrations reais,
backfill legado, downgrade/upgrade e validação do isolamento recebido.

## Validação do código combinado

`CONFIRMADO`:

- `python -m pytest -q tests/unit/load_planning tests/unit/test_multi_truck_optimizer.py`:
  **497 passed**, 16,07 s.
- Configuração de migrations e readiness: **12 passed**, 1,60 s.
- `python -m ruff check .`: aprovado.
- `python -m ruff format --check .`: aprovado, **616 arquivos**.
- `git diff --check`: aprovado após o merge.

`CONFIRMADO`: suíte completa novamente executada no código combinado:

- `TEST_DATABASE_URL=<PostgreSQL local loadx_test> python -m pytest -q tests --cov=app --cov-report=term`:
  **3.310 passed**, sete warnings, **788,49 s**; cobertura **95%**
  (16.943 statements, 883 missed). Inclui integração e E2E, inclusive as novas
  seis verificações G03-B2, migrations, RBAC e testes HTTP de limite.
- `alembic check` contra o banco exclusivo no schema atualizado:
  **No new upgrade operations detected.** Models e migrations são compatíveis.
- Não houve falha funcional ou teste pendente. Os números históricos de 3.304
  testes continuam no relatório original e não são reutilizados como evidência
  deste merge. Os sete warnings são de dependências/deprecações e do teste que
  provoca duplicidade de identidade para verificar a constraint.

`CONFIRMADO`: nova consulta ao remoto após os testes confirmou desenvolvimento
em 4cf4e923 e a branch publicada ainda em c366fb9e. Além do merge recebido, esta
atualização altera somente este registro, o aviso/link no README histórico e a
exceção específica em docs/evidencias/.gitignore. Logs e artefatos de cobertura
ficam fora do commit. Push previsto exclusivamente normal, sem rebase/amend ou
reescrita. O estado remoto e o SHA final são conferidos após a publicação.

`CONFIRMADO`: limite público mantido em 200. Os testes HTTP da Issue #430 verificam
recusa antecipada de 201/500/1.000 volumes em plano, comparação, preflight e
otimização. A proposta de job continua pendente de decisão de Rennan. Nenhuma
fila, deploy, PR ou alteração de frontend integra esta atualização.
