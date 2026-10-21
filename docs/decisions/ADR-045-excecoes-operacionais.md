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
