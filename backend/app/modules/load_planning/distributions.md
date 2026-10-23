# Contrato multi-caminhão — OC87

`CONFIRMADO`: contrato aditivo da Issue #130; decisões propostas na
[ADR-028](../../../../docs/decisions/ADR-028-planejamento-multi-caminhao.md).
Não seleciona frota automaticamente (OC88), não cria UI (OC89) e não implementa
operação final de entregas parciais (OC90).

## OC88 — necessidade e proposta

`CONFIRMADO`: `LoadDistributionService.preflight(DistributionNeedRequest)` recebe
order_ids de pedidos READY, materializa as unidades com identidade original
(order_item_id,volume_index), dimensões/peso, sequência e regras físicas, e retorna
caminhões elegíveis e inelegíveis com motivo. Não persiste nem reserva frota.
`create(DistributionCreate, changed_by=ator)` recebe a partição escolhida: parts
contém truck_id e volumes (order_item_id,volume_index). Aceita 1–10 caminhões
**distintos**, até 200 volumes no total; cada parte tem pelo menos uma unidade.
O service obtém dados/ator no servidor; payload não fornece posições, produto,
pedido do volume ou estados. Schema recusa campos extras/identidades duplicadas.

`CONFIRMADO`: a união das partes deve ser exatamente a expansão dos pedidos.
A mesma engine física calcula cada subconjunto pela entrada pública
`calculate_volume_load_plan`, sem renumerar volumes nem alterar rotação, apoio,
peso, colisão, profundidade ou sequência. Fonte inválida, frota indisponível,
duplicação, omissão ou rejeição física desfaz tudo. DISTRIBUTION_CAPACITY_REJECTED
(422) informa truck_id, identidades e motivos da engine em details; não persiste
plano parcial inválido. OC88 pode tentar outra partição usando o mesmo contrato.


## OC88 — otimização automática multi-caminhão

`CONFIRMADO`: `POST /api/v1/load-distributions/optimize` recebe somente
`order_ids` e reutiliza o `preflight` da OC87 para materializar os volumes e
obter a fotografia atual da frota elegível. O algoritmo puro fica em
`optimizer/multi_truck.py`; ele não acessa banco, HTTP ou FastAPI.

A busca tenta completar a necessidade com um caminhão antes de ampliar para
dois, três e assim sucessivamente, até o limite de dez partes definido pela
OC87. Cada tentativa usa exclusivamente `calculate_volume_load_plan`; portanto,
dimensões, peso, rotações, colisão, apoio, fragilidade, profundidade e sequência
continuam pertencendo à engine física existente.

O desempate entre soluções completas com a mesma quantidade de veículos é
determinístico: menor capacidade volumétrica total da frota escolhida, menor
capacidade total de peso, UUIDs dos caminhões e, por fim, identidades dos
volumes atribuídos. A ordem recebida do banco ou do payload não define o
resultado.

Para controlar custo síncrono, estados parciais equivalentes são deduplicados
e a fronteira de busca é limitada deterministicamente. A estratégia continua
sendo uma heurística sobre `heuristic-v1`, e não um solver global exato de
bin-packing 3D.

Uma solução só é persistida quando cobre todos os volumes. Depois da escolha,
o service converte o resultado em `DistributionCreate` e chama o mesmo
`LoadDistributionService.create`, que bloqueia/revalida a frota e recalcula
cada subconjunto antes do commit. Mudança de disponibilidade entre preflight e
persistência continua produzindo o erro operacional existente.

Se nenhuma combinação pesquisada completar a necessidade, a API retorna
`DISTRIBUTION_CAPACITY_INSUFFICIENT` (422), com volumes restantes, motivos
físicos observados, caminhões inelegíveis no preflight e quantidade de
tentativas da busca. Nenhum plano parcial é persistido.

## OC89 — HTTP e consulta

`CONFIRMADO`: prefixo `/api/v1/load-distributions`:

| Método/caminho | Contrato |
|---|---|
| POST /preflight | DistributionNeedRequest -> DistributionNeedRead, 200, sem escrita |
| POST /optimize | DistributionNeedRequest -> DistributionRead, 201, seleção automática OC88 |
| POST prefixo | DistributionCreate -> DistributionRead, 201, proposta completa |
| GET /{distribution_id} | DistributionRead, 200 |
| POST /{distribution_id}/approve | corpo `{}`, aprova todas as partes, 200 |
| POST /{distribution_id}/cancel | corpo `{}`, cancela proposta inteira, 200 |
| POST /{distribution_id}/parts/{part_id}/approve | corpo `{}`, aceita parte, 200 |
| POST /{distribution_id}/parts/{part_id}/cancel | corpo `{}`, cancela parte, 200 |
| POST /{distribution_id}/parts/{part_id}/reprocess | truck_id e expected_load_plan_id, 200 |

`CONFIRMADO`: DistributionRead informa id/status/created_by/created_at UTC,
order_ids, truck_count, volume_count, parts e volumes. Cada parte contém `truck` (TruckSnapshotRead histórico do plano), UUID estável,
status e LoadPlanRead completo (truck_id, ocupação/peso, volumes/snapshots, posições,
rejeições e plano de origem). volumes explicita parte, proveniência, índice original
e quantidade original; quantidade nunca é a contagem parcial por caminhão.
Detalhe/visualização 3D dos planos mantêm endpoints e schemas anteriores.

`CONFIRMADO`: operações são exclusivas de LOGISTICS_MANAGER; ADMIN e gestor
consultam; CHECKER consulta somente distribuição APPROVED; DRIVER é negado.
Cookie, Origin/CSRF, minimização de logs e envelope ErrorResponse existentes
continuam válidos. Erros de fonte/frota reutilizam códigos atuais; 404 também
cobre agregado/parte inexistentes, inclusive parte de outra distribuição.

## Ciclo, cancelamento e idempotência

`CONFIRMADO`: partes PENDING/APPROVED/CANCELED; aprovação da parte é aceitação da
proposta. Pedidos permanecem READY e planos CALCULATED até aprovação total.
Agregado PROPOSED -> PARTIALLY_APPROVED -> APPROVED; uma só parte pode ir direto
a APPROVED. Aprovação total confirma planos APPROVED e pedidos PLANNED com
histórico no mesmo commit. Repetição de aprovação/cancelamento é idempotente.
Aprovação parcial nunca libera um plano para operação.

`CONFIRMADO`: cancelar parte antes do total produz INCOMPLETE; seus volumes continuam
reivindicados pela necessidade, aguardando reprocessamento. Reprocessar conserva
parte e identidades, grava novo plano recalculated_from_id e retorna PENDING.
expected_load_plan_id é controle otimista: concorrência/reenvio com versão antiga
retorna DISTRIBUTION_VERSION_CONFLICT, sem descendente duplicado. Outra parte
permanece intacta. Redistribuição entre partes exige cancelamento integral e nova
proposta. Cancelamento integral conserva histórico/planos e libera claims; pedidos
permanecem READY. Agregado APPROVED é imutável nesta OC, inclusive antes de operação.
Cancelamento posterior depende da coordenação da OC90/OC94.

`CONFIRMADO`: aprovação/recálculo legados de qualquer versão de plano da distribuição
retornam LOAD_PLAN_SOURCE_CHANGED; use o agregado. Aprovação legada com pedido
reivindicado e transição manual READY -> DRAFT/CANCELED são bloqueadas. Simulações
legadas continuam permitidas, mas não podem apropriar volumes já reivindicados.

## Integridade, concorrência e OC90

`CONFIRMADO`: PostgreSQL é fonte da verdade. Claims ativos têm unicidade de pedido
e identidade de volume; PK/FKs compostas validam proveniência e mesma parte/necessidade.
CHECK limita índice a 1..quantidade; triggers diferidas verificam cobertura exata,
mesmos volumes/ordens dos planos, caminhões distintos e estados coerentes no COMMIT,
inclusive em escrita direta. Migrations testam upgrade/downgrade e head único.
Locks ordenados serializam aprovação, reprocessamento e disputa de necessidades.
Erros de integridade conhecidos viram DISTRIBUTION_INTEGRITY_CONFLICT sem SQL bruto.

`CONFIRMADO`: caminhão ativo/disponível é revalidado na proposta e aprovação sob
TruckService.ensure_no_operation_conflict. Aprovação não reserva frota (ADR-023):
necessidades diferentes podem propor o mesmo veículo, e a reserva operacional
continua pertencendo ao carregamento/viagem. Nenhum motorista é escolhido e as
regras OC64/65 permanecem intactas. preflight não garante disponibilidade futura.

`CONFIRMADO`: OC90 recebe parte/LoadPlan, itens/identidades, pedido, histórico e
cadeia de versões. Carregamento e viagem continuam identificados pelo LoadPlan;
LOAD_DISTRIBUTION/LOAD_DISTRIBUTION_PART ampliam o histórico consultado pela OC97.
O port público get_distribution_part_for_plan resolve plano atual/histórico em
necessidade, parte estável, current_load_plan_id, estados e identidades de volume;
consumidores não acessam tabelas internas do planejamento.
OperationalLoadPlan expõe operational_ready: true no legado e, pela OC90, para
qualquer parte APPROVED de distribuição APPROVED usando seu plano atual. Versões
históricas/reprocessadas permanecem false. Loading/Trip rejeitam uso prematuro.
A OC90 recompõe o pedido pelas entregas das partes necessárias sem alterar a
identidade dos volumes ou a entrega única do legado sem distribuição.

`PENDENTE DE DEFINIÇÃO`: revisão humana das ADR-028/044.
`CONFIRMADO`: a UI OC89 já integra a base.
Cancelamento após aprovação continua pertencendo à OC94.
`RISCO IDENTIFICADO`: snapshots são históricos; recálculo usa cadastros atuais e
não reescreve outras partes. Limites síncronos e disponibilidade não são promessa
de solução ótima ou reserva. Não há purge de necessidade/plano/histórico pela API.

## Recuperação no frontend — OC89

`CONFIRMADO`: `GET /load-plans` acrescenta `distribution_id` anulável aos resumos,
sem carregar itens. A consulta resolve também as versões anteriores por sua cadeia
persistida. O detalhe `GET /load-plans/{id}` informa o mesmo vínculo. O frontend
abre `/planning/distributions/{id}` e consulta o agregado; nunca otimiza ao reabrir.
Não há nova tabela, migration, listagem paralela ou persistência local de propostas.

`CONFIRMADO`: permissões efetivas atuais são `loadx.planning.read`,
`loadx.planning.create` e `loadx.planning.approve` (OC112). ADMIN e gestor de sistema
possuem as três; CHECKER continua restrito a leitura de aprovados, DRIVER não lê.
Perfis personalizados seguem seu catálogo no servidor. A matriz antiga acima é
histórica e não amplia nem restringe as permissões efetivas da OC112.



## OC90 — continuidade operacional

`CONFIRMADO`: get_operational_plan libera qualquer quantidade de partes somente
quando distribuição/parte estão APPROVED e o plano é o atual. Histórico continua
rastreável e bloqueado. get_distribution_part_for_plan projeta IDs de pedidos,
identidades e partes da distribuição; get_distribution_order_for_part projeta
somente as partes que contêm volumes de um pedido, inclusive sem viagem criada.
Consumidores continuam sem acesso às tabelas internas.

`CONFIRMADO`: Delivery referencia parte, uma por parte/pedido. Aprovação mantém
PLANNED; primeiro início move IN_TRANSIT; somente todas as pernas necessárias
concluídas entregam o pedido. Triggers OC90 preservam estrutura/status da
distribuição desde a primeira entrega. A fotografia inteira do plano e seus
pedidos/itens congela desde a primeira LoadingSession ou Trip, inclusive legado.
Fonte dos volumes permanece aqui; auditoria
reconstrói distribuição → parte → plano → loading → trip → delivery → pedido.
ADR-044 documenta cardinalidade/locks como proposta para revisão. Não altera a
UI OC89 nem implementa cancelamento/reentrega OC94.


## Recuperação idempotente — #254

`CONFIRMADO`: contrato implementado para revisão na ADR-047. Tabela aditiva
`optimization_requests`: PK (user_id, request_key), payload_hash SHA-256 de
versão/seleção ordenada, distribution_id único com FK RESTRICT, created_at UTC.
Persistência atômica com distribuição/planos/volumes/histórico; sem pending ou TTL.
`POST /load-distributions/optimize` aceita header UUID `Idempotency-Key` opcional.
Replay igual retorna 201 com o mesmo recurso atual; payload diferente: 409
IDEMPOTENCY_PAYLOAD_MISMATCH. Concorrência: 409 OPTIMIZATION_IN_PROGRESS.
`GET /load-distributions/optimization-requests/{key}` retorna 200/404/409,
somente para o ator e com a mesma permissão create. Não cria nada.
Migration 20261023_0035 → 20261021_0034; downgrade recusa registros existentes.
Sem alteração de regras físicas, RBAC efetivo, MFA ou OC90/OC94.
