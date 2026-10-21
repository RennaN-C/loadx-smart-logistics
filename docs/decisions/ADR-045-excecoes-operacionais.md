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
