# ADR-043 — Outbox persistente e resultado incerto

Status: proposta técnica da OC109 (#156), implementada para revisão.

## Decisão

`CONFIRMADO`: PostgreSQL 16 é a fila. Fato OC84, destinatários OC103 e evento
outbox são inseridos na mesma transação do domínio. Não há broker obrigatório.
Identidade UUID, origem notification_id única, contrato v1 e canal WHATSAPP_MOCK;
correlação e chave idempotente são imutáveis. Payload é referência à notificação,
sem telefone, texto, token ou headers. Não há webhook de saída aprovado: OC83 é entrada.

Estados: PENDING, PROCESSING, SUCCEEDED, RETRYABLE, TERMINAL, UNCERTAIN.
Claim usa FOR UPDATE SKIP LOCKED, lease com prazo e geração monotônica (fencing).
Tentativa é confirmada antes do adapter; I/O ocorre sem transação aberta. Resultado
somente é aceito se geração e lease continuam válidos. Lease expirado torna a
operação UNCERTAIN; nunca repetir automaticamente um envio possivelmente realizado.
Timeout/erro desconhecido também é UNCERTAIN. Erros transitórios conhecidos antes
do efeito podem repetir com backoff exponencial limitado e jitter; permanentes
terminam. Número máximo configurável por ciclo; histórico total nunca reinicia.

`CONFIRMADO`: somente o mock OC82 está habilitado. Não promete entrega externa nem
exactly-once. Um futuro adapter real precisa contrato aprovado de timeout,
idempotência do provedor e classificação antes de habilitar. Fencing protege o
banco, não desfaz efeito remoto. Worker separado processa uma tentativa por vez;
SIGTERM encerra após a tentativa atual. Crash deixa lease para recuperação.

## Compatibilidade e corte

`CONFIRMADO`: migration aditiva 20261020_0027 sobre head real 20261020_0026.
Backfill não envia: SIMULATED/NO_RECIPIENT são concluídos; FAILED é terminal;
ATTEMPT_CLAIMED é incerto; NOT_ATTEMPTED é pendente. Estados originais nunca são
reiniciados. Tentativas legadas são identificadas no histórico como LEGACY.
O dispatcher compatível da OC84 continua aceitando providers mock injetados;
worker e dispatcher disputam o mesmo claim OC84. Worker observa resultado legado
sem repetir. Novas tentativas da outbox não reescrevem estados terminais OC84.
Caixa pessoal, leitura e preferências independem do resultado do canal.

`CONFIRMADO`: ADMIN pode consultar e reprocessar somente RETRYABLE/TERMINAL/UNCERTAIN
com confirmação e chave UUID idempotente. Por ser exclusivamente mock, resultado
incerto admite repetição explícita; isso não autoriza replay real. Comandos ficam
persistidos e auditados atomicamente. Mesmo retry do comando não reinicia duas vezes.
Outros papéis, inclusive CUSTOM, não recebem nova permissão delegável nesta OC.

## Segurança e operação

`CONFIRMADO`: erros são códigos de catálogo, nunca exception text/trace/payload.
API não devolve telefone/conteúdo/chave de provider. Payload v1 não aceita campos
extras e limita-se a UUIDs; não há API de publicação arbitrária. Tentativas e
comandos preservados sem expurgo automático; retenção requer política aprovada.
Downgrade recusa filas/históricos/comandos não vazios. Pausar escritores antigos,
aplicar migration, trocar aplicação e iniciar worker; não executar deploy nesta OC.

`RISCO IDENTIFICADO`: indisponibilidade do worker acumula fila; monitorar contadores,
idade e heartbeat por execução. Não existe alerta externo ou webhook novo nesta OC.

`CONFIRMADO`: reprocessamento bloqueia primeiro a conta autorizada com lock
compartilhado e o evento com FOR UPDATE; somente então insere o comando com FK.
Isso evita deadlock de promoção de KEY SHARE entre comandos simultâneos. A
regressão sincroniza explicitamente os dois processos antes do lock do evento.
