# ADR-028: necessidade e distribuição de volumes entre caminhões

Status: proposta na OC87 (#130), para revisão humana do PR

## Contexto

`CONFIRMADO`: ADR-005 identifica o volume por `(order_item_id, volume_index)`
1-based; ADR-014 persiste snapshots em LoadPlanItem. LoadPlan possui um caminhão.
ADR-023 reserva caminhões somente no carregamento/viagem, não na aprovação.
A operação atual associa um pedido inteiro a uma entrega (ADR-022).

## Decisão proposta

`RECOMENDAÇÃO`: LoadDistribution representa a necessidade completa de um ou mais
pedidos READY. Seus volumes são exatamente a expansão das quantidades dos itens,
com a identidade original, nunca quantidades renumeradas por veículo. Cada volume
pertence a exatamente uma parte estável; cada parte referencia um LoadPlan e,
por ele, um caminhão. Um pedido pode aparecer em várias partes da mesma necessidade,
mas não em duas necessidades ativas. Índices únicos de claims ativos protegem
pedidos e volumes, inclusive contra concorrência e escrita fora do service.

`RECOMENDAÇÃO`: propostas aceitam de um a dez caminhões distintos, até 200 volumes
no total. O consumidor informa a partição exata dos volumes, não posições/MIME/IA.
A engine existente valida/calcula cada subconjunto com as mesmas regras físicas.
Nenhuma seleção global automática é implementada: OC88 escolhe a partição e usa
o service. Rejeição física, ausência de identidade, duplicação ou falta de frota
recusa a operação inteira, sem salvar uma solução parcial. O erro de capacidade
informa veículo e volumes rejeitados. A disponibilidade consultada é uma fotografia;
cada escrita e aprovação a verifica novamente sob lock.

`RECOMENDAÇÃO`: partes têm PENDING, APPROVED e CANCELED; aprovação de uma parte é
aceitação da proposta, não liberação física do LoadPlan. Enquanto incompleta ou
parcialmente aprovada, todos os pedidos permanecem READY e os planos CALCULATED.
A aprovação total exige todas as partes aprovadas, cobertura exata e caminhões
ativos/disponíveis. No mesmo commit, planos viram APPROVED, pedidos READY -> PLANNED
e seus históricos são gravados. Não criar estados novos de pedido. Repetição de
aprovação é idempotente; conflitos e falhas revertem todas as mudanças.

`RECOMENDAÇÃO`: distribuição usa PROPOSED, PARTIALLY_APPROVED, APPROVED, INCOMPLETE
ou CANCELED. Antes da aprovação total, cancelar uma parte produz INCOMPLETE,
mantém os volumes na necessidade e impede aprovação total. Reprocessar essa parte
mantém seu UUID e exatamente suas identidades, aceita outro caminhão, cria novo
LoadPlan com recalculated_from_id e exige nova aprovação da parte. Demais partes
não mudam. Redistribuir volumes entre partes exige cancelar a proposta inteira e
criar outra; não mutar silenciosamente a necessidade. Cancelamento integral libera
claims, preserva volumes/planos/histórico e mantém pedidos READY. APPROVED é imutável
nesta OC: cancelar/recalcular depois da liberação exige coordenação operacional da
OC90/OC94, ficando bloqueado. Não apagar registros históricos.

`RECOMENDAÇÃO`: aprovação/reprocessamento legados de planos pertencentes à
distribuição são bloqueados; usar o agregado. Aprovar plano legado com pedidos
reivindicados por necessidade ativa também é bloqueado. Transições manuais de
pedidos reivindicados são negadas. Consultas e visualização 3D dos planos continuam
usando os contratos atuais e snapshots, sem duplicar renderização.

`RECOMENDAÇÃO`: transações seguem locks de distribuição, caminhões em ordem UUID,
planos em ordem UUID, pedidos/itens em ordem UUID e produtos. Criação não possui
distribuição anterior e começa pelos caminhões. Unicidade, FKs, CHECKs e triggers
de integridade diferidas validam cobertura e vínculo parte/plano/volume no COMMIT.
Histórico LOAD_DISTRIBUTION e LOAD_DISTRIBUTION_PART amplia o catálogo existente;
LOAD_PLAN e ORDER continuam auditados no mesmo commit. Não depender de memória.

`RECOMENDAÇÃO`: aprovação não reserva caminhão, conforme ADR-023; não alterar OC64/65.
Caminhão ocupado é inelegível na proposta/aprovação. Propostas concorrentes com
pedidos diferentes podem citar o mesmo caminhão disponível; a operação futura
continua reservando sob o service de conflitos existente. Não escolher motorista
nesta OC; o vínculo e conflito continuam sob o service de viagens.

## Contratos e compatibilidade

`RECOMENDAÇÃO`: OC88 recebe necessidade materializada/identidades e frota elegível,
propõe a partição, persiste atomicamente e recebe rejeições sem planos parciais.
OC89 consulta agregado, UUIDs estáveis das partes, planos, veículos, métricas,
volumes e aprovação. OC90 consulta volumes por plano/parte e histórico: carregamento
e viagem continuam por LoadPlan, sem duplicar caminhão. Entrega parcial não é um
novo estado de pedido; futura conclusão deve recompor as partes antes de DELIVERED.

`CONFIRMADO`: o caminho legado de um caminhão continua sem exigir agregado.
`RECOMENDAÇÃO`: uma distribuição com uma parte completa pode usar a operação atual
após aprovação total. Com várias partes, a fronteira operacional bloqueia uso pelo
fluxo legado até OC90: ele ainda pressupõe entrega única por pedido e não pode
marcar um pedido inteiro entregue ao concluir uma fração. Esta proteção não
implementa a operação final nem muda viagens/comprovantes existentes.

`PENDENTE DE DEFINIÇÃO`: revisão/aprovação humana da ADR; integração operacional de
entregas parciais (OC90) e cancelamento depois de liberação (OC94).
`RISCO IDENTIFICADO`: limites síncronos atuais permanecem; propostas grandes não
são uma solução assíncrona nem promessa de capacidade ótima. Disponibilidade não
é reserva e pode mudar entre aprovação e operação.
