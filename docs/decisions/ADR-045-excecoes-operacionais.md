# ADR-045 — OC94: ledger de tentativas de excecao

Estado: implementacao inicial proposta. A OC94 NAO ESTA CONCLUIDA.

O modelo OC90 usa estados restritos e preserva comprovantes e partes fisicas multi-caminhao.
Nao se deve adicionar cancelamento ao status operacional sem reconciliar sessoes de
carregamento pendentes, reserva do veiculo, volumes e outbox.

Decisao desta primeira entrega:
- Nova tabela aditiva de eventos por entrega, sem alterar viagens, pedidos ou comprovantes.
- Eventos: ausencia, recusa, avaria, falha operacional, reagendamento e retomada informativa.
- Cada tentativa exige motivo, autor e chave UUID de idempotencia; retries identicos
  retornam o evento original e payload divergente com mesma chave recebe 409.
- Registro somente para viagem IN_ROUTE e entrega nao concluida.
- A consulta respeita a autorizacao ja implementada pela OC90.
- Reagendamento registra data futura mas NAO muda a rota nem agenda do caminhao.
- Nao emitir notificacao ficticia nem dar baixa em volumes nesta fase.
- A migration protege o historico de downgrade destrutivo.

PENDENTE para encerramento da OC94: transicoes de cancelamento, interrupcao e
retomada com bloqueios fisicos, reserva do caminhao, etapas de carregamento,
integração de UI, outbox, testes de concorrencia e multi-caminhao E2E.

## Sequência de tentativas operacional

- Ausência, recusa, avaria ou falha operacional abrem ocorrência pendente.
- Enquanto existir ocorrência pendente, entrega e comprovante não podem ser
  concluídos: a operação retorna 409 sob o lock OC90, sem baixa de volumes.
- `RESCHEDULED` exige falha aberta e data futura com fuso; **não** remonta
  cargas ou altera a agenda/rota automaticamente.
- `RESUMED` exige falha ou reagendamento pendente; reagendamento futuro impede
  retomar antes do combinado. Depois da retomada, a entrega original avança
  normalmente, sem duplicar parte, pedido ou comprovante.
- Uma falha adicional exige encerrar a tentativa anterior por retomada.
- Cancelamento físico e liberação de reservas continuam fora deste recorte.


## Pré-validação de cancelamento (sem efeito colateral)

Endpoint `GET /api/v1/trips/{trip_id}/cancellation-preflight` para
ADMIN/gestores com `trips.manage`, com autorização por objeto.

O retorno é um **parecer de segurança operacional**, não um cancelamento.
`safe_for_cancellation_workflow=true` significa somente que uma transação
completa de cancelamento pode ser preparada e revisada. Nenhuma reserva é
liberada por este GET. São bloqueios explícitos:

- `TRIP_ALREADY_STARTED_OR_FINISHED`: só viagens ainda SCHEDULED;
- `LOADING_SESSION_EXISTS`: inclusive PENDING, pois já pode reservar caminhão;
- `DELIVERY_ALREADY_STARTED_OR_MISSING`: todas as entregas devem estar PENDING;
- `MULTI_TRUCK_PART_REQUIRES_RECONCILIATION`: não liberar parte isolada nem
  marcar pedido agregado como cancelado sem reconciliar os demais caminhões.

Antes de habilitar um POST irreversível, reconciliar dentro de **uma**
transação com locks ordenados: viagem, entregas, plano/caminhão,
sessão de carregamento, pedidos e partes de distribuição; garantir
unicidade dos volumes físicos, histórico e eventual outbox. A API existente
não pode simplesmente mudar `Trip.status` ou chamar cancelamento de
distribuição já aprovada. O retorno da pré-validação pode ficar obsoleto
por concorrência: a implementação futura **deverá revalidar tudo sob lock**.

**Pendência explícita:** execução do cancelamento e liberação de recursos
ainda não são suportadas. Não apresentar o preflight como ação concluída.

## Proposta de contrato: cancelamento transacional (aguardando revisão)

Esta seção registra a **próxima fase de implementação**, ainda **não aprovada**
nem habilitada por API. Foi preparada após a integração da OC90, considerando os
contratos reais de `Trip`, `Delivery`, `LoadPlan`, `LoadingSession`,
`LoadDistributionPart`, `Order` e a reserva de caminhão/motorista.
A pré-validação GET já disponível **não concede autorização para mutação**.

### Restrições observadas no código de 21/10/2026

1. `trips.status` aceita apenas `SCHEDULED`, `IN_ROUTE` e `FINISHED`;
   o CHECK de timestamps também depende desses três estados. Acrescentar
   `CANCELED` exige migration aditiva, atualização do modelo e histórico.
2. `deliveries.status` aceita apenas `PENDING`, `IN_DELIVERY` e
   `DELIVERED`. Não remover entregas já vinculadas nem simular
   `DELIVERED` para permitir o cancelamento.
3. `TruckRepository.has_operation_conflict` considera a existência de
   `LoadingSession` e `Trip.status != FINISHED`; uma viagem
   `CANCELED` sem adaptar esse filtro **continuaria reservando caminhão**.
   O conflito de motorista também consulta viagens ativas.
4. `trips.load_plan_id` é único e `LoadPlan.status` não tem estado
   `CANCELED`. Plano aprovado, pedidos `PLANNED` e volumes referenciados
   não podem ser simplesmente eliminados ou marcados como disponíveis.
5. Entregas OC90 vinculam `distribution_part_id` a volumes físicos
   identificados por `(order_item_id, volume_index)`, com partes irmãs.
   Cancelar uma viagem não equivale a cancelar toda a distribuição.

### Matriz de elegibilidade proposta

| Estado observado sob lock | Política inicial | Justificativa |
| --- | --- | --- |
| `SCHEDULED`, nenhuma `LoadingSession`, todas as entregas `PENDING`, sem `distribution_part_id` | Candidato para cancelamento transacional **somente após** contrato de planejamento/pedidos | Ainda é preciso reconciliar plano aprovado e reservas |
| Qualquer `LoadingSession` (`PENDING`, em curso ou finalizada) | Bloquear | Carregamento já pode ter reservado caminhão e volumes |
| `IN_ROUTE` ou `FINISHED` | Bloquear | Viagem iniciada tem efeitos operacionais e/ou comprovantes |
| Qualquer entrega fora de `PENDING`, ausência de entregas ou comprovante existente | Bloquear | Não apagar entrega, histórico ou comprovação |
| Entrega vinculada a `distribution_part_id` | Bloquear **neste incremento** | Exige reconciliação de todas as partes e volumes sob lock |
| Repetição da mesma chave idempotente, com mesmo payload, após sucesso | Retornar resultado persistido | Evitar dupla baixa/reserva e histórico duplicado |
| Mesma chave idempotente, payload diferente | `409` | Chave não representa duas intenções diferentes |

O campo `safe_for_cancellation_workflow` do GET significa apenas
**elegibilidade preliminar**. O POST deverá executar novamente as validações
**dentro da transação**, pois estado e reservas podem mudar após a consulta.

### Contrato de comando proposto, não implementado

- `POST /api/v1/trips/{trip_id}/cancellation`, somente
  `loadx.trips.manage` e com checagem de acesso ao objeto.
- Corpo estrito: `reason` não vazio e limitado, `idempotency_key` UUID;
  identidade do autor vem da sessão autenticada, nunca do payload.
- Resposta de sucesso deverá incluir referência de auditoria e estado
  persistido; `409` estável para cada impedimento; `404` se a viagem
  não existe; `401/403` sem vazar existência a quem não possui acesso.
- Um registro persistente e único por viagem documentará autor, horário,
  motivo, idempotência e resultado. Não usar delete em cascata de viagem,
  entrega, plano, comprovante ou volume.
- `Trip.CANCELED` e sua constraint de timestamp exigem migration
  **nova**, descendente do head atual. A transição não deve atualizar
  `started_at` ou `finished_at` com valores artificiais.

### Transação e isolamento necessários antes de habilitar o POST

1. Reaproveitar a ordem de locks da OC90 para viagem, entregas e demais
   entidades, coordenando plano/caminhão, carregamento, pedidos e distribuição
   sem introduzir inversão de locks com aprovação ou início de viagem.
2. Revalidar sob lock todas as condições da matriz e qualquer concorrência
   com criação de carregamento, início de viagem e entrega.
3. Resolver primeiro a política de **plano aprovado e pedidos `PLANNED`**:
   cancelar apenas a viagem libera o caminhão, mas pode deixar o pedido
   preso no planejamento aprovado; reverter o pedido para `READY` sem
   invalidar referências ativas também seria incorreto. Esta política
   requer contrato com o módulo de planejamento antes de escolher uma
   mutação definitiva.
4. Quando a política for aprovada, persistir mudança de estado, ledger de
   cancelamento e histórico na **mesma transação**, com rollback completo
   em erro; garantir que os predicados de reserva de caminhão **e**
   motorista deixem de contar viagens canceladas, sem liberar uma sessão
   de carregamento que permaneça ativa.
5. Não emitir `TRIP_STARTED` nem ocorrência/notificação de cancelamento
   sem fato e contrato aceitos por OC84/OC103/OC109. Qualquer outbox
   futura deverá ser inserida na mesma transação com chave idempotente.
6. Manter os dados físicos e de comprovantes intactos; nada de reatribuição
   automática de `distribution_part_id` ou de volumes entre caminhões.

### Evidências exigidas para liberar a implementação

- Migrations upgrade/downgrade seguro, com histórico preservado e verificação
  das constraints e dos predicados de reserva.
- PostgreSQL 16 real: sucesso elegível, bloqueio de loading `PENDING`,
  loading finalizado, trip em rota/finalizada, entrega movida, ausência de
  entregas, pedido com outro vínculo, parte multi-caminhão e comprovante.
- Dois comandos concorrentes com mesma chave (um efeito) e diferentes chaves
  (um vencedor), disputa com início de viagem/loading e rollback injetado.
- Verificar que caminhão/motorista ficam disponíveis **somente** após
  confirmação do commit e que pedido, plano e volumes não entram em estado
  impossível após erro.
- Provar `401/403/404/409`, autorização efetiva de ADMIN/gestor, proibição
  de DRIVER/CHECKER sem permissão, e evitar vazamento de dados.
- UI de confirmação só após API transacional e esses testes; nada de
  exibir cancelamento como concluído enquanto houver apenas preflight.

**Decisão pendente para aprovação:** definir junto ao domínio de planejamento
se cancelar uma viagem agendada sem loading também invalida o plano aprovado,
como os pedidos retornam à elegibilidade de replanejamento e como o sistema
audita essa transição. A implementação do POST e o desbloqueio dos cenários
multi-caminhão ficam condicionados a essa reconciliação. Até lá, manter o
endpoint físico e seus botões desabilitados.
