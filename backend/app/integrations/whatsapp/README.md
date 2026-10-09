# WhatsApp — OC82

`CONFIRMADO`: WhatsAppProvider mantém receive_message/send_response e DTOs
independentes do fornecedor. MockWhatsAppProvider continua padrão, sem rede ou
credenciais. A proposta Meta usa httpx2 existente, sem SDK, tabela ou migration.
Decisão e limites: [ADR-035](../../../../docs/decisions/ADR-035-adapter-whatsapp-business.md).

`DECISÃO NECESSÁRIA`: a Issue #125 não registra fornecedor aprovado. Meta é
recomendação para revisão; confirmar fornecedor/API e credenciais no ambiente
antes de habilitar envio. Nenhuma chamada real foi usada na implementação/testes.

## Configuração

`CONFIRMADO`: parâmetros vêm de app/core/config.py. Segredos devem ser injetados
pelo ambiente seguro, nunca pelo request, frontend, repositório ou log.

| Variável | Padrão / uso |
|---|---|
| WHATSAPP_PROVIDER | mock; meta seleciona a proposta de adapter real |
| WHATSAPP_REAL_ENABLED | false; habilitar explicitamente somente após aprovação |
| WHATSAPP_ACCESS_TOKEN | vazio; token bearer fornecido pelo ambiente |
| WHATSAPP_PHONE_NUMBER_ID | vazio; identificador do número no painel Meta, somente dígitos |
| WHATSAPP_API_VERSION | vazio; versão Graph API vigente aprovada, formato vN.N |
| WHATSAPP_COUNTRY_CODE | vazio; código de país explícito para telefones nacionais do cadastro |
| WHATSAPP_TIMEOUT_SECONDS | 5; limite de cada fase connect/read/write/pool, de 0.1 a 30 s |
| WHATSAPP_MAX_ATTEMPTS | 2; de 1 a 3 tentativas, somente antes de transmissão |
| WHATSAPP_RETRY_BACKOFF_SECONDS | 0.25; de 0 a 2 s, exponencial entre tentativas seguras |

`CONFIRMADO`: meta sem habilitação/token/número/versão válidos falha com
WHATSAPP_NOT_CONFIGURED antes do IO. Não há fallback silencioso. Para desabilitar,
restaurar WHATSAPP_PROVIDER=mock e WHATSAPP_REAL_ENABLED=false e reiniciar todos
os workers. Reiniciar também após rotação de credenciais; seleção é por processo.

`CONFIRMADO`: compose.yaml carrega .env local não versionado;
compose.production.yaml encaminha as variáveis ao backend pelo ambiente do host.
Não imprimir configuração expandida com token. Exemplos versionados deixam
credenciais e versão vazias. Número de teste/token devem ser obtidos no painel
do fornecedor aprovado, sem compartilhar o token em Issue/PR/chat.

## Envio e retorno

`CONFIRMADO`: send_response recebe destinatário e texto (1–4096 caracteres).
Formato internacional exige + e dígitos; telefone nacional usa o normalizador do
cadastro e WHATSAPP_COUNTRY_CODE explícito, sem inferir país. O POST usa host fixo
graph.facebook.com, bearer no header, TLS, sem redirects/proxy implícito.

`CONFIRMADO`: resultado preserva campos legados e acrescenta provider_message_id
e accepted_at UTC somente após resposta válida. sent_at legado é o horário de
criação da mensagem; aceitação não comprova entrega/leitura. OC83 tratará retornos.
Texto livre depende da janela de atendimento e consentimento verificados pelo
chamador; não há criação/envio de template, mídia ou disparo promocional nesta OC.

| Código normalizado | Operação |
|---|---|
| WHATSAPP_NOT_CONFIGURED | revisar seleção, habilitação e ambiente |
| WHATSAPP_INVALID_MESSAGE | corrigir destinatário/conteúdo antes de enviar |
| WHATSAPP_AUTHENTICATION_FAILED | revisar/rotacionar credencial no ambiente seguro |
| WHATSAPP_REJECTED | rejeição 4xx/redirect; revisar contrato/política |
| WHATSAPP_RATE_LIMITED | limite externo; não repetir operação de domínio |
| WHATSAPP_TIMEOUT / WHATSAPP_UNAVAILABLE | transporte/serviço indisponível |
| WHATSAPP_INVALID_RESPONSE | aceitação não validável; resultado pode ser incerto |
| WHATSAPP_IDEMPOTENCY_UNAVAILABLE | envio com identidade exige guard durável |
| WHATSAPP_IDENTITY_CONFLICT | identidade reutilizada com conteúdo diferente |
| WHATSAPP_SEND_IN_DOUBT | reserva sem receipt; reconciliar antes de qualquer reenvio |
| WHATSAPP_INCOMING_UNSUPPORTED | recepção real pertence à OC83 |

`CONFIRMADO`: retries automáticos somente em ConnectTimeout, PoolTimeout ou
ConnectError anteriores ao POST. Erros de leitura/escrita, 408/5xx e resposta
inválida usam delivery_uncertain=true e nunca são reenviados automaticamente.
Código Graph 190 em HTTP 400 é autenticidade inválida; 4/80007/130429/131048/131056
são limites de envio. Outros 4xx, inclusive janela encerrada 131047, são rejeição.
4xx/429 não são repetidos pelo adapter. Timeout é por fase, não prazo total de
parede; limite de tentativas e backoff evita loop ilimitado.

## Idempotência e OC79

`CONFIRMADO`: operation_id UUID opcional identifica um envio. Se informado no
adapter real, exige SendGuard injetado por composição confiável. Sem guard,
falha antes do IO; não cria uma falsa garantia em memória no provider real.

`CONFIRMADO`: claim precisa reservar atomicamente antes do IO, persistir entre
workers/restarts e comparar fingerprint de destinatário normalizado/texto.
Receipt concluído é reutilizado sem POST; conflito ou reserva sem receipt bloqueia
reenvio. Complete guarda somente sucesso validado. Falha de persistência após
aceitação retorna resultado incerto, mantendo a reserva. InMemorySendGuard é um
double para testes/mock, limitado e sem remoção automática de identidades.

`PENDENTE DE DEFINIÇÃO`: implementação durável, retenção, reconciliação e outbox
OC109; consumers OC84 que exigem idempotência devem fornecer essa port antes do
envio. Envios legados sem operation_id são best-effort; nova chamada pode duplicar
mensagem. Não há promessa de exactly-once nem reaproveitamento indevido da tabela
external_commands como histórico de envios.

`CONFIRMADO`: bearer de saída não autentica comandos de entrada. OC83 deve usar
autenticidade/bindings confiáveis e ExternalCommandService da OC79. Resposta é
posterior ao commit; receipt.duplicate não deve disparar novo envio. Nunca executar
comando novamente para recuperar notificação. Provider não acessa banco/services.

## Simulação, operação e observabilidade

`CONFIRMADO`: POST /api/v1/messages/interpret permanece autenticado com sessão,
Origin/CSRF e RBAC ADMIN/LOGISTICS_MANAGER; usa exclusivamente mock mesmo quando
saída real estiver selecionada. Simulação não autentica remetente WhatsApp.
Gatilhos legados de notificação continuam posteriores ao commit e best-effort.
Falha externa não desfaz transação de negócio confirmada.

`CONFIRMADO`: WHATSAPP_SEND_ACCEPTED, WHATSAPP_SEND_FAILED e WHATSAPP_SEND_RETRY
usam loadx.operations, request_id, código fechado e tentativa; sucesso pode conter
operation_id UUID. Não incluem telefone, texto, token, número do remetente,
provider_message_id ou body externo. Logs httpx2/httpcore2 são suprimidos somente
durante envio sensível, preservando logs de outras integrações.

`CONFIRMADO`: validação sem credenciais reais, na pasta backend:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest -q tests/unit/test_whatsapp_meta.py tests/unit/test_whatsapp_provider.py
```

`CONFIRMADO`: testes PostgreSQL de messages_api/notifications_api cobrem RBAC,
simulador isolado, transação confirmada e repetição de status sem segundo envio.
Executar conforme tests/integration/README.md ou CI; transport usa MockTransport.

`PENDENTE DE DEFINIÇÃO`: fornecedor/ativação, assinatura/webhook/mídia OC83,
eventos/templates OC84 e persistência/reprocessamento OC109.
