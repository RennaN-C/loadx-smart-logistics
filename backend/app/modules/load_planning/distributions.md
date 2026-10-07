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

## OC89 — HTTP e consulta

`CONFIRMADO`: prefixo `/api/v1/load-distributions`:

| Método/caminho | Contrato |
|---|---|
| POST /preflight | DistributionNeedRequest -> DistributionNeedRead, 200, sem escrita |
| POST prefixo | DistributionCreate -> DistributionRead, 201, proposta completa |
| GET /{distribution_id} | DistributionRead, 200 |
| POST /{distribution_id}/approve | corpo `{}`, aprova todas as partes, 200 |
| POST /{distribution_id}/cancel | corpo `{}`, cancela proposta inteira, 200 |
| POST /{distribution_id}/parts/{part_id}/approve | corpo `{}`, aceita parte, 200 |
| POST /{distribution_id}/parts/{part_id}/cancel | corpo `{}`, cancela parte, 200 |
| POST /{distribution_id}/parts/{part_id}/reprocess | truck_id e expected_load_plan_id, 200 |

`CONFIRMADO`: DistributionRead informa id/status/created_by/created_at UTC,
order_ids, truck_count, volume_count, parts e volumes. Cada parte tem UUID estável,
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
OperationalLoadPlan acrescenta operational_ready: true no legado e na
necessidade completa de uma parte após aprovação; false para múltiplas partes ou
versões históricas. Loading/Trip rejeitam uso prematuro. Não modificar pedidos,
entregas/comprovantes/evidências por uma fração sem recomposição: a operação multi
permanece bloqueada até OC90, preservando a entrega única do legado.

`PENDENTE DE DEFINIÇÃO`: revisão humana da ADR-028 e integração dos consumidores
OC88/OC89/OC90; liberação operacional/cancelamento após aprovação são das OCs próprias.
`RISCO IDENTIFICADO`: snapshots são históricos; recálculo usa cadastros atuais e
não reescreve outras partes. Limites síncronos e disponibilidade não são promessa
de solução ótima ou reserva. Não há purge de necessidade/plano/histórico pela API.
