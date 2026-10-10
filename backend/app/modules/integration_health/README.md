# Integrações e Saúde — OC108

`CONFIRMADO`: GET `/api/v1/integration-health`, ADMIN ativo, somente leitura,
sem parâmetros de provider, teste de envio, prompt, upload ou credenciais.
Reusa liveness de `/health` e o mesmo checker PostgreSQL/Alembic de `/ready`.
Sem model/repository/migration: não há novos dados persistentes.

Resposta: `checked_at` UTC, `correlation_id` UUID igual ao X-Request-ID,
`overall_status` PARTIAL/DEGRADED e seis `components` com `component`, `mode`,
`status`, `configured` (boolean/null) e `reason_code` de catálogos fechados.
HTTP 200 contém falhas parciais; 401/403 preservam autorização existente.
Nenhuma configuração bruta, URL, nome arbitrário de provider, payload, telefone,
token, stack trace ou mensagem de exceção é devolvida. Headers no-store existentes.

- API: liveness compartilhada; não certifica prontidão do banco.
- Banco: readiness real de PostgreSQL/head Alembic. Checker aplica seu timeout
  existente (2 s); await externo acrescenta 1 s de limite. Falhas viram códigos
  seguros, sem detalhar host, schema, credenciais ou revision interna.
- WhatsApp: sempre MOCK/SIMULATED por ADR-036/037; nenhuma prova de envio Meta.
- IA: factory atual é fake local; configuração mock mostra SIMULATED. Nome externo
  no ambiente não instala nem aprova provider e mostra NOT_CONFIGURED. Nunca
  exibe o valor de AI_PROVIDER, que poderia conter informação indevida.
- Webhook: NOT_IMPLEMENTED/OC83_PENDING; simulador não é recepção HTTP real.
- Notificações: INTERNAL/LIMITED/OC84_PENDING. Base existente envia avisos de
  início de viagem e ocorrência após commit para o mock; evolução OC84 pendente.

## Sinais futuros aprovados

`CONFIRMADO`: `IntegrationHealthSource.read_signal(timeout_seconds=...)` é port
assíncrona de metadata para adapters aprovados, sem executar envio/prompt. Retorna
somente `IntegrationSignal(mode, configured, approved, status)`. Registro ocorre
explicitamente no servidor (`app.state.integration_health_sources`), junto ao
componente efetivamente implementado pela OC responsável; não há configuração
HTTP, discovery, ativação por nome no ambiente ou adapter real implementado aqui.

IA requer modo REAL e aprovação/configuração para AVAILABLE; webhook e notificações
requerem INTERNAL. Registro de WhatsApp é ignorado para preservar a política mock.
Sinais têm limite de 1 s e são consultados em paralelo; adapter deve cooperar com
cancelamento e nunca iniciar trabalho durável ou IO funcional. Timeout/falha/sinal
inválido não quebra demais indicadores. Configuração desconhecida vira null.

PARTIAL indica capacidades simuladas/limitadas/pendentes, inclusive quando API e
banco estão prontos. DEGRADED indica falha/timeout. Não se usa um "saudável geral"
para ocultar ausência de integrações reais.

`CONFIRMADO`: falhas emitidas como INTEGRATION_HEALTH_FAILED, reason permitido e
request_id, sem mensagens de exceção. UUID/data permitem rastrear esta consulta
nos logs operacionais existentes. Não há histórico persistido, contagem de envios,
retries, outbox (OC109), webhook (OC83), evolução notificações (OC84) ou OC103.
Política: ADR-036 e ADR-037; não exige nova ADR nem altera decisões existentes.
