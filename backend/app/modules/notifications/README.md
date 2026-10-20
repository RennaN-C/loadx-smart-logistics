# Notificações operacionais — OC84

`CONFIRMADO`: implementação persistente autorizada pela
[revisão técnica da PR #226](https://github.com/RennaN-C/loadx-smart-logistics/pull/226#issuecomment-6289881953).
WhatsApp continua exclusivamente mock (ADRs 036/037). Não há rota pública ou UI nova.

## Registro interno e canal

`operational_notifications` registra na transação do domínio:

- `TRIP_STARTED`: UUID do histórico efetivo `TRIP: SCHEDULED → IN_ROUTE`;
- `OCCURRENCE_REGISTERED`: UUID da ocorrência efetivamente gravada.

TripService/OccurrenceService usam o service público deste módulo para preparar a
linha antes do commit, mesmo sem provider injetado. Falha na gravação desfaz o fato
e histórico. A linha existe independentemente da simulação; não é recibo de envio.
Não copia texto, telefone, credenciais ou payload. O motorista é identidade
operacional histórica, não usuário autorizado da futura central.

## Integridade e estados

`CONFIRMADO`: FKs RESTRICT, CHECKs e dois índices UNIQUE parciais protegem
(tipo, origem, motorista). INSERT ON CONFLICT aguarda concorrentes sem abortar a
transação. Triggers PostgreSQL conferem origem/transição/viagem/destinatário,
protegem identidade e origens referenciadas e fecham transições de tentativa.
A origem é bloqueada com FOR SHARE durante a validação para impedir alteração
concorrente entre a leitura da proveniência e o INSERT.

| mock_status | Significado |
|---|---|
| NOT_ATTEMPTED | Registro durável, nenhuma tentativa reclamada |
| ATTEMPT_CLAIMED | Claim confirmado; resultado ainda desconhecido |
| SIMULATED | Mock retornou normalmente; não comprova envio/entrega real |
| FAILED | Mock falhou; domínio permanece confirmado |
| NO_RECIPIENT | Sem telefone/motorista ativo ou vínculo atual elegível; sem mock |

Claim e resultado têm timestamps distintos. Estado terminal não volta para
NOT_ATTEMPTED. Alteração de vínculo/atividade é relida sob lock de viagem e
motorista antes da simulação, sem reendereçar a outra pessoa nem copiar telefone.

## Fronteira transacional

`CONFIRMADO`: após o commit durável, `dispatch_after_commit` usa outra Session
ligada ao Engine. UPDATE condicional NOT_ATTEMPTED → ATTEMPT_CLAIMED concede uma
única tentativa e é confirmado **antes** de chamar o mock. Depois, outra transação
revalida o destinatário e grava o resultado. Falhas dessa etapa nunca fazem rollback
do domínio já confirmado. `MockNotificationSender` concentra formatação/telemetria
do canal, sem representar persistência por si só.

Sessions ligadas à Connection podem apenas liberar savepoints: não autorizam
simulação nem claim. Na OC79, `transfer_staged` encaminha somente IDs/handlers ao
dono da transação; ele despacha depois de sair do `db.begin()` externo. Replay não
executa domínio nem despacha outra vez. OC83 utiliza essa composição integrada.
Os hints em `Session.info` são voláteis, não são fila nem fonte de verdade; a linha
PostgreSQL permanece NOT_ATTEMPTED se o processo morrer antes do claim.

Uma composição customizada com transação externa precisa transferir os hints e
chamar dispatch após seu próprio commit. Sem isso, mantém o registro interno sem
simular. O simulador existente conserva sua confirmação explícita: cria o fato
interno, mas não injeta um segundo aviso automático.

`RISCO IDENTIFICADO`: crash entre commit/claim mantém NOT_ATTEMPTED; após claim
ou falha ao confirmar resultado mantém ATTEMPT_CLAIMED, inclusive se o mock já
retornou. Não há retry, varredura, worker ou promessa exactly-once. OC109 definirá
recuperação; OC103 definirá central, preferências e autorização por destinatário.
Não há backfill de mensagens fictícias ou inclusão de eventos novos.

## Arquivos e rastreabilidade

- `models.py`, `repository.py`, `service.py`: persistência, unicidade e composição;
- `sender.py`: mock/telemetria sanitizada, sem conteúdo/telefone em logs;
- migration `20261020_0025` sobre `20261016_0024`, aditiva e sem perda de dados;
- [ADR-041](../../../../docs/decisions/ADR-041-notificacoes-operacionais-duraveis.md).

A consulta interna por ID é somente leitura. Logs carregam tipo, UUID da viagem,
UUID da notificação e correlação técnica; exceções não incluem mensagem/trace.
401/403, Origin/CSRF e permissões continuam nos comandos operacionais existentes.
Downgrade recusa banco que já contenha notificações.

## Validação

`CONFIRMADO`: testes PostgreSQL 16 exclusivos em `test_durable_notifications.py`,
`test_notifications_api.py`, `test_notification_commit_regression.py` e
`test_external_commands.py`. Cobrem persistência/recriação de services, concorrência
por conexões independentes, rollback, claim visível antes do mock, savepoints,
replay OC79, falhas/crashes, privacidade e consultas sem escrita.

Executar a suíte conforme `backend/tests/integration/README.md`; nunca usar dados
reais. A OC89 permanece integrada; a OC90 não foi antecipada nem copiada. Notificação
sempre se refere à viagem efetiva, independentemente da origem de seu plano.
