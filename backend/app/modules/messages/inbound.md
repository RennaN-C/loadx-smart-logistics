# Webhook HTTP controlado — OC83

`CONFIRMADO`: `POST /api/v1/webhooks/controlled-events` recebe comandos HTTP de
emissor controlado. Não é webhook Meta: sem handshake, API externa, número real
ou confirmação WhatsApp. Simulador `/messages/interpret` e saída mock permanecem.

## Autenticidade e normalização

`CONFIRMADO`: header único `X-LoadX-Signature` contém HMAC-SHA-256 dos bytes
originais completos, hexadecimal minúsculo de 64 caracteres, com chave exclusiva.
`HmacExternalAuthenticator` verifica em tempo constante antes de JSON/domínio.
Content-Type application/json (charset UTF-8 opcional), sem compressão.

`CONFIRMADO`: corpo é exatamente o envelope v1 da OC79, sem wrapper:
version, event_id, subject, command, target_id, issued_at, expires_at. Somente
START_TRIP (target viagem), START_DELIVERY e FINISH_DELIVERY (target entrega).
Normalização é validação tipada pela OC79, preservando bytes/fingerprint;
não há texto livre, inferência de entrega atual, telefone ou comandos novos.

`CONFIRMADO`: máximo 16 KiB; objeto JSON estrito, sem campos extras/chaves
duplicadas; versão inteiro 1 (não bool/string), UUID explícito, datas ISO-8601
com timezone. event_id/subject: 1–128 caracteres `[A-Za-z0-9_.:-]`. Validade
máxima 5 minutos; expiração exclusiva e tolerância futura de 30 segundos.
Expirado é rejeitado mesmo já concluído; retry válido é deduplicado, não bypass.

## Configuração opt-in e identidade

| Variável | Contrato |
|---|---|
| INBOUND_WEBHOOK_ENABLED | boolean; padrão false |
| INBOUND_WEBHOOK_SIGNING_KEY | segredo exclusivo, mínimo 32 bytes UTF-8, diferente de SECRET_KEY; sem padrão |
| INBOUND_WEBHOOK_BINDINGS | objeto JSON subject -> UUID de usuário, provisionado no servidor |
| INBOUND_WEBHOOK_CAPABILITIES | array JSON com subconjunto não vazio dos três comandos |

`CONFIRMADO`: enabled exige chave, bindings e capabilities; configuração
ausente/inválida impede iniciar. Erros de Settings omitem inputs. Desabilitado
retorna 503 INBOUND_NOT_CONFIGURED sem ler corpo ou acessar banco. Chave pode vir
do ambiente seguro ou arquivo INBOUND_WEBHOOK_SIGNING_KEY via LOADX_SECRETS_DIR.
Não versionar segredo ou passá-lo em argumento; revogação exige reiniciar workers.

`CONFIRMADO`: namespace estável `loadx-controlled-webhook`. Binding imutável
resolve subject assinado; nenhum campo do cliente concede identidade/permissão.
OC79 revalida capabilities, atividade, papel e vínculo de motorista sob locks;
services públicos aplicam autorização de objeto e estado. Não há impersonação.

`CONFIRMADO`: apenas POST no caminho exato substitui Origin/cookie/CSRF por HMAC.
Outras rotas/métodos preservam proteção. Cookie sozinho não autentica emissor.
O header não é liberado no CORS: contrato servidor-servidor. TLS fora de loopback
é obrigatório; HMAC não cifra tráfego. Gestão segura de bindings/chave é do operador.

## Respostas e transação

`CONFIRMADO`: 200 `{id: UUID, duplicate: false}` na primeira execução; mesmos
bytes/ator retornam mesmo id e duplicate true. UNIQUE PostgreSQL/INSERT ON
CONFLICT da OC79 serializam concorrência e sobrevivem a reinícios. Mesmo event_id
com bytes/ator incompatíveis retorna 409. Até espaços/ordenação alteram fingerprint.
Reenvio exige autenticidade, autorização e validade atuais.

`CONFIRMADO`: claim, domínio e histórico compartilham transação externa OC79;
rollback libera identidade para retry dentro da validade, inclusive falha após
commit de savepoint. Não há IO externo, outbox, retry automático ou OC109.

| HTTP | code |
|---|---|
| 400 | INBOUND_HEADERS_INVALID / INBOUND_REQUEST_INCOMPLETE |
| 401 | EXTERNAL_AUTHENTICITY_INVALID |
| 403 | EXTERNAL_COMMAND_FORBIDDEN |
| 408 | INBOUND_BODY_TIMEOUT |
| 409 | EXTERNAL_IDENTITY_CONFLICT / EXTERNAL_DOMAIN_REJECTED |
| 410 | EXTERNAL_COMMAND_EXPIRED |
| 413 | INBOUND_BODY_TOO_LARGE |
| 415 | INBOUND_CONTENT_TYPE_INVALID |
| 422 | EXTERNAL_PAYLOAD_INVALID / EXTERNAL_COMMAND_NOT_YET_VALID |
| 429 | INBOUND_BUSY, Retry-After 1 |
| 500 | EXTERNAL_PROCESSING_FAILED |
| 503 | INBOUND_NOT_CONFIGURED, Retry-After 1 |

`CONFIRMADO`: erro segue code/message/details genéricos. Headers/limite podem
ser rejeitados antes de assinatura, sempre sem domínio/persistência. Falha
inesperada/DB é 500 sanitizado da OC79, com rollback. Retry conserva event_id,
bytes e assinatura dentro da validade; não repetir cegamente 403/conflito/estado.
Após expiração, conferir estado antes de emitir outra intenção com novo evento.

## Limites, logs e mídia

`CONFIRMADO`: 4 recebimentos por worker, sem fila, incluindo leitura/execução;
corpo tem 5 s de orçamento, inclusive sem Content-Length. Pool dedicado de 4,
espera 2 s, conexão 2 s, lock_timeout 2 s e statement_timeout 5 s. Não há prazo
global de transação, rate limit distribuído ou promessa anti-DDoS. Workers
multiplicam o limite; controle global/por emissor pertence ao proxy/infraestrutura.

`CONFIRMADO`: correlation_id dos eventos reutiliza X-Request-ID gerado no servidor.
Somente código/resultado e UUID de receipt são logados; nunca body, subject,
event_id, telefone, assinatura, segredo, mensagem, imagem/base64 ou traceback.
INBOUND_WEBHOOK_REJECTED cobre transporte; EXTERNAL_COMMAND_* mantém OC79.

`CONFIRMADO`: mídia está desabilitada, mesmo com storage local opt-in da OC80.
Comando de mídia, links, base64 ou campos extras retornam 422 EXTERNAL_PAYLOAD_INVALID.
Não há endpoint falso, fetch externo ou gravação. `PENDENTE DE DEFINIÇÃO`: contrato
inbound autenticado de mídia/replay e coordenação storage/commit. OC80 requer
Session própria com commit real; savepoint OC79 não confirma IO durável. Produção,
retenção e provider continuam dependentes de aprovação ADR-027 e #193.

Homologação com HTTP real e dados fictícios: `infra/scripts/README.md`.
