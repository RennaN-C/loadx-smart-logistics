# OC90 — evidências operacionais e integridade

`CONFIRMADO`: a PR existente é a [#231](https://github.com/RennaN-C/loadx-smart-logistics/pull/231),
na branch `marcelo/oc90-fluxo-multi-caminhao`. A integração atual com OC109 está
registrada em [reconciliação OC90/OC109](reconciliacao-oc109.md), com novos testes,
conflitos, inventário e resultados. Esse relatório é a evidência da base combinada.

## Histórico anterior à OC109

`CONFIRMADO`: o commit `163b59d0d6aac60cdc14aa3392cb4ef714148590` foi publicado
sobre `41e00bd0690070c0965b75b2fdb0fbd46d5e9d68`, antes da integração OC109.
Naquela rodada passaram 87 testes focados, 1.294 de regressão, 2.620 backend com
95% de cobertura e 925 frontend. Ruff validou 467 arquivos; lint/build/bundle
budget passaram. Esses números históricos **não** validam a nova base OC109.
A correção atual preserva esse commit e usa merge/commits novos e push normal.

## Integridade preservada

`CONFIRMADO`: optimize real força duas partes e conserva identidades disjuntas
`(order_item_id, volume_index)`. Aprovação libera somente planos atuais. Checklists,
viagens, entregas e comprovantes são independentes. A primeira viagem inicia o
pedido uma única vez; somente a última perna necessária o entrega. Falha em B
não desfaz A. PDFs e StatusHistory permitem reconstruir o fluxo; legado preservado.

`CONFIRMADO`: a primeira LoadingSession ou, defensivamente, Trip congela linhas
inteiras de LoadPlan, LoadPlanOrder e LoadPlanItem, inclusive no legado. Guardas
PostgreSQL usam `ck_load_plans__operational_snapshot`; no-op é permitido. Escrita
concorrente em filho tenta pais antigos/novos em UUID crescente com NOWAIT para
não esperar pelo pai que possa estar criando a FK do checklist nesse filho.
Contenção exige rollback/retry, inclusive antes da operação. Loading bloqueia o
plano e atualiza snapshots/itens em cache antes de materializar o checklist.

`CONFIRMADO`: 51 mutações diretas cobrem caminhão/snapshots/métricas/algoritmo,
identidade/exclusão do plano, posição/rotação/dimensões/sequência, snapshots dos
produtos e inserção/exclusão/reatribuição de itens/pedidos. A constraint é verificada
explicitamente. Criação, aprovação e reprocessamento pré-operacionais continuam
válidos. Há testes de no-op, mapas obsoletos e concorrência PostgreSQL real.

`CONFIRMADO`: a migration OC90 é agora
`20261020_0028_delivery_distribution_parts.py`, sobre a outbox OC109 `0027`.
Downgrade com entregas de parte falha antes de DDL, sem apagar histórico. A
[ADR-044](../../decisions/ADR-044-entregas-por-parte-distribuicao.md) permanece
**proposta implementada para revisão**. ADR-025 e minimização continuam vigentes;
nenhum evento, ID de domínio, PII ou payload novo foi acrescentado aos logs OC90.

`PENDENTE DE DEFINIÇÃO`: aceite formal da ADR-044 e nova revisão da PR #231.
A UI OC89 e a fila administrativa OC109 vêm da base, sem implementação paralela.
Cancelamento/reentrega OC94 permanece fora do escopo. Não há deploy ou merge em
desenvolvimento; validação local não equivale à aprovação dos checks/revisor.
