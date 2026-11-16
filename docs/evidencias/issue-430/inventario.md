# Issue #430 — inventário da fronteira física

`CONFIRMADO`: base `cb9c6f7d7f0e1b2829cae938a15e2fc63d6be09e`.
Volumes físicos, linhas de pedido, pedidos e caminhões são contagens diferentes.
Um único item com quantity=201 já excede o limite; 200 linhas com quantity=1 não.

| Camada | Local | Limite/função preservada |
| --- | --- | --- |
| Engine | optimizer/engine.py | MAX_VOLUMES=200; preflight soma quantity antes de expandir; subset valida contagem/identidade |
| Expansão | optimizer/volumes.py | quantity positiva → identidades 1..quantity; helper puro sem limite próprio, protegido pelos chamadores |
| Ordenação | optimizer/ordering.py | volume, peso, flags, entrega e UUID/índice; Decimal em contexto dedicado |
| Rotações | optimizer/rotations.py | prioridade XYZ/XZY/YXZ/YZX/ZXY/ZYX; simetrias deduplicadas |
| Pontos | optimizer/placement.py | origem + três faces positivas; ordem y,z,x,rotation_rank; first-fit |
| Colisão | optimizer/geometry.py | AABB inteiro; apenas sobreposição positiva; contato permitido |
| Apoio | optimizer/support.py | união exata de contatos por altura, 100%, todos os ancestrais, sem tolerância |
| Peso | optimizer/weight.py | Decimal finito/positivo; igualdade permitida; só aceitos acumulam |
| Profundidade/sequência | optimizer/loading_sequence.py | porta z=L; entrega posterior mais profunda; Kahn com desempates explícitos |
| Métricas | optimizer/metrics.py | somente colocados, Decimal/ROUND_HALF_UP, heuristic-v1 |
| Final | engine._revalidate_final_result | partição, atributos, limites, rotações, colisões, apoio, profundidade, sequência, peso e métricas |
| Plano/comparação HTTP | service.py | count antes da engine; comparação independente não persiste, preflight valida todos os candidatos |
| Comparação pura | optimizer/comparison.py | 2–10 candidatos distintos; mesma carga até 200; ordem de resposta acompanha entrada |
| Distribuição pura | optimizer/multi_truck.py | até 10 partes; 64 estados **na fronteira por nível**, não 64 avaliações totais; cache por capacidade completa + identidades |
| Distribuição HTTP | distribution_service.py | _sources limita soma a 200 antes da expansão; preflight exclui inelegíveis; rollback da leitura antes de CPU; revalida snapshots/frota sob lock na persistência |
| Schemas distribuição | distribution_schemas.py | order_ids max_length=200 (pedidos); volumes max_length=200 (identidades por parte); total de identidades <=200; parts max_length=10 |
| Schemas comparação | schemas.py | truck_ids min_length=2/max_length=10; não confundir com unidades físicas |
| Erro HTTP | router._calculation_error_response | 422 LOAD_PLAN_VOLUME_LIMIT_EXCEEDED; volume_count e max_volumes; distribuição reutiliza o mapeamento |
| Persistência | models.py/distribution_models.py | contagens não negativas; BIGINT de volume geométrico; índices/FKs de identidade; sem CHECK novo de 500/1.000 |
| UI de seleção | PlanBuilder.tsx | MAX_SYNC_VOLUMES=200; soma volume_count, não item_count; botão/preflight protegidos |
| UI de planejamento | PlanningPage.tsx, load-planning/README.md | textos/erro explicam limite de 200 |
| Recuperação | useOptimizationRecovery.ts | seleção local de até 200 order_ids; não é prova do número de volumes |
| Cena/tabela | LoadScene.tsx, PlanItemsTable.tsx | map de todos os volumes; uma instância React/mesh por volume, sem virtualização de milhares |

`CONFIRMADO`: nenhum desses limites públicos foi ampliado nesta entrega. Os
arquivos físicos alterados são engine.py, geometry.py e loading_sequence.py;
support/placement/rotations/ordering/weight/volumes/metrics/contracts e a busca
multi preservam suas implementações. Não há migration nem alteração frontend.

`RISCO IDENTIFICADO`: o preflight automático lista **toda** a frota elegível;
MAX_DISTRIBUTION_TRUCKS limita partes/profundidade, não tamanho dessa entrada.
Não foi introduzido corte de candidatos que mudaria a escolha. Frota maior que a
matriz medida precisa de orçamento próprio. Cache permanece local, mas guarda
resultados por capacidade/subconjunto; resultados contêm rejeições e referências
a volumes, logo custo cresce com frota distinta e estados, além de N.

`CONFIRMADO`: propostas completas reaproveitam o resultado calculado somente
quando capacidade e todos os atributos físicos conferem após locks. Alterar
fonte dispara recálculo. Idempotency-Key e recuperação da ADR-047 não cancelam
CPU nem convertem otimização em job. Aprovação/operacionalização não mudaram.

`PENDENTE DE DEFINIÇÃO`: configuração efetiva do Render (CPU, RAM, instâncias,
concorrência e timeout de proxy) não está declarada no repositório. O Compose de
referência usa BACKEND_WORKERS=2 por padrão, sem orçamento de CPU/RAM por cálculo.
Não há SLO aprovado nas ADR-013/046/047. Não foi consultado nem sobrecarregado o
serviço publicado. Sem esses dados e validação end-to-end, um tempo favorável da
função pura não basta para habilitar uma capacidade HTTP maior.
