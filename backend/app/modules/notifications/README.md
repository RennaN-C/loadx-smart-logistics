# Notificações operacionais — OC84

`CONFIRMADO`: implementação persistente autorizada pela
[revisão técnica da PR #226](https://github.com/RennaN-C/loadx-smart-logistics/pull/226#issuecomment-6289881953).
WhatsApp continua exclusivamente mock (ADRs 036/037). A OC84 não criou rotas ou UI;
a OC103 acrescenta a central pessoal descrita abaixo.

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
recuperação; OC103 implementa central, preferências e autorização pessoal.
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


## Central pessoal — OC103

`CONFIRMADO`: ADR-042, sobre OC84 integrada pela PR #226. `inbox_repository.py`,
`inbox_service.py`, `schemas.py` e `router.py` compõem a API pessoal, sem alterar
estados/tentativas de canal. `notification_recipients` e `notification_preferences`
são persistidas pela revision 20261020_0026. Nenhum GET materializa destinatários.

Recebimento ocorre na mesma transação do fato. Seleção usa os services públicos
de usuários/perfis (OC112); somente a primeira inserção do fato fixa destinatários.
Replay não adiciona novas contas. Viagens exigem trips.read; ocorrências exigem
também occurrences.read; a identidade DRIVER vinculada/ativa recebe suas operações.
ADMIN recebe sua própria cópia, sem acesso a leitura/preferência de outro usuário.
Consulta e origem revalidam grants e vínculo atuais, sem transferir histórico.

A listagem retorna PageResponse + unread_count global no mesmo snapshot SQL,
com filtros page/page_size/sort_order/event_type/category/read. Contador, leitura
individual, leitura em lote, preferências e origem usam /api/v1/notifications;
contratos completos em docs/05. Primeira leitura é imutável/idempotente no banco;
marcar todas é UPDATE único da caixa visível no snapshot, sem marcar fatos futuros.

Preferências TRIPS/OCCURRENCES afetam só novas associações; SECURITY é obrigatória
por schema/CHECK, sem inventar eventos. USER_UPDATED audita mudanças de campos,
sem valores, mensagens ou PII. Alertas documentais/manutenção futuros devem vir dos
services donos com contrato aprovado; não há duplicação de elegibilidade ou worker.

Backfill usa contas autorizadas no corte, com data de recebimento do corte,
sem afirmar identidade histórica anterior. Downgrade com destinatários/preferências
é recusado. `RISCO IDENTIFICADO`: a entrega deve coordenar a migration e a troca
dos escritores; uma versão antiga ainda gravando após o corte não conhece a nova
associação. Não há recuperação de canal ou retries automáticos da OC109 nesta OC.

`CONFIRMADO`: `test_notification_inbox.py`
cobre isolamento, ADMIN sem personificação, RBAC/custom grants, vínculo atual,
preferências, auditoria/rollback, concorrência, snapshots, paginação com empate,
idempotência e backfill/downgrade seguro. A suíte completa inclui regressões OC84,
OC79, OC83 e OC89 em PostgreSQL 16.

## OC109 — fila de eventos e reprocessamento

`CONFIRMADO`: [ADR-043](../../../../docs/decisions/ADR-043-outbox-retentativas.md).
`outbox_models/repository/service/router/schemas.py` acrescentam saída durável e
administração; `worker.py` é processo separado, sem depender do ciclo HTTP.
Contrato e tabelas em docs/03–05. WhatsApp continua **somente simulado**. Não há
webhook de saída aprovado; webhook OC83 continua sendo entrada autenticada.

### Execução local e Render (configuração proposta, sem deploy)

1. Pausar escritores/worker antigos e confirmar backup; aplicar `alembic upgrade head`.
2. Atualizar API e escritores externos para a mesma revisão. Nenhum `stamp`, reset
   ou alteração de migrations antigas. Não iniciar worker antes da migration.
3. Criar processo Background Worker no Render com a mesma imagem/dependências e
   configuração segura do backend. Root directory `backend`, comando
   `python -m app.modules.notifications.worker`. A URL do banco e os segredos vêm
   do ambiente; não colocar valores em comandos/versionamento. Sem porta pública.
4. Executar uma réplica inicialmente; múltiplas usam SKIP LOCKED. Verificar contadores,
   idade do pendente mais antigo e logs `outbox_result`, além do histórico paginado.
5. SIGTERM/SIGINT param novos claims e aguardam a chamada mock corrente; engine é
   descartado. Interrupção abrupta deixa lease; próximo worker registra UNCERTAIN.
   Erro de banco causa espera, sem log de mensagem/trace/URL/credenciais.

Parâmetros validados em Settings: `OUTBOX_LEASE_SECONDS` (60, 10–600),
`OUTBOX_MAX_ATTEMPTS` (5, 1–20), `OUTBOX_BASE_SECONDS` (30),
`OUTBOX_CAP_SECONDS` (3600), `OUTBOX_POLL_SECONDS` (2, 0.1–60).
Backoff = min(cap, base*2^(tentativa-1)) × uniforme[0.5,1]. Limites por ciclo;
reprocessamento explícito começa outro ciclo sem apagar tentativas/gerações.
Não há expurgo automático. Payload v1 contém apenas referência UUID (16 bytes),
não aceita corpo arbitrário e não armazena mensagem/telefone.

### Compatibilidade e falhas

Backfill/adotação de SIMULATED/NO_RECIPIENT conclui sem reenviar; FAILED exige
intervenção; ATTEMPT_CLAIMED permanece incerto. Estados OC84 não reiniciam. O
caminho de dispatch mock compatível pode completar antes do worker; o mesmo claim
OC84 impede envio adicional. Worker nunca repete canal já tentado na versão antiga.
Novos retries têm histórico independente, sem alterar estados terminais da OC84.
Caixa, leitura e preferências OC103 continuam independentes.

Adapter em `app/integrations/outbox.py` reutiliza provider OC82. Rejeição definitiva
é TERMINAL; falha transitória **com garantia de ausência de efeito** é RETRYABLE;
timeout/erro desconhecido/crash são UNCERTAIN. Fencing protege resultado no banco;
não cancela um efeito remoto. Nenhum adapter real está habilitado, nem se promete
exactly-once. Novo transporte exige contrato de idempotência/timeout aprovado.

### Administração

Configurações → Fila de eventos usa API real, filtros/paginação/histórico e origem
reautorizada. Somente ADMIN ativo consulta e reprocessa; nenhum grant novo delegável.
POST exige CSRF/Origin e UUID de comando. Replay desse UUID não reabre o evento;
reutilização para outro ator/origem retorna 409. Estado e comando/auditoria
OUTBOX_REPROCESSED são atômicos. Lease ativo e sucesso não são reprocessáveis.
Resultado incerto permite ação explícita apenas porque o canal é mock.

Downgrade vazio testado; com qualquer evento/auditoria OC109, é recusado para
preservar histórico. Correção com dados deve ser por migration aditiva. Não apagar
fila para permitir downgrade em produção. Monitorar volume e retenção antes de
crescimento operacional; não há política aprovada de descarte ou alerta externo.


## Consulta contextual da entrega — OC81

`CONFIRMADO`: `communication_router/service/repository/schemas.py` expõem
`GET /api/v1/deliveries/{delivery_id}/communications`. É uma projeção somente
leitura dos fatos já persistidos, sem novas tabelas, eventos ou tentativas.
OccurrenceReferenceService fornece a seleção exata por entrega e viagem;
o repository de notificações consulta somente suas próprias tabelas e essa
fronteira pública. `TRIP_STARTED` e ocorrências sem vínculo com a entrega são
excluídos. Não há inferência por pedido, motorista ou texto.

A autorização reutiliza TripService para leitura de entrega e vínculo/atividade
do motorista, além de exigir permissão efetiva de leitura de ocorrências.
Consulta não acessa destinatários/preferências/read_at da OC103 nem expõe
mensagens, telefone, payload, tokens, correlação, erro interno ou comandos da
fila administrativa. Somente canal simulado, origem, UUID e datas/status.
O processamento pode ainda não ter fila (legado): nesse caso o campo é null;
não é inventado um resultado. Paginação padrão de vinte/máximo cem, ordenação
determinística `(created_at,id)` e direção asc/desc. GET não chama provider,
materializa registros, marca leitura ou reprocessa fila.

`CONFIRMADO`: este contrato aditivo foi autorizado pela operação coordenada de
conclusão v1.2.0; completa a consulta que faltava na OC81, preservando caixa
pessoal e a administração da OC109 como fluxos distintos.


## Auditoria de processos — #256/#273

`CONFIRMADO`: `tests/integration/test_outbox_process_recovery.py` acrescenta
cinco cenários PostgreSQL 16 com subprocessos novos, incluindo encerramento
abrupto pós-claim, backoff/cap, disputa PENDING/RETRYABLE, fencing e API ADMIN.
Usa exclusivamente MockOutboxTransport e adapters de falha, sem envio externo.
Fixtures de API usam commits reais para não prender locks em savepoints do
processo pai. Evidência incremental em
`docs/evidencias/qa-v12-pentest/lote-outbox-processos.md`.
