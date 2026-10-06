# Produção

Configuração de referência para publicar o frontend próprio e a API sob a mesma
origem HTTPS. Não contém domínio, credencial nem dado real.

## Pré-requisitos

- DNS de `LOADX_DOMAIN` apontando para o servidor.
- Portas TCP 80/443 liberadas para o Caddy obter e renovar TLS. HTTP/3 está
  desativado nesta referência, portanto UDP 443 não é necessário.
- PostgreSQL 16 externo ou privado, já preparado com
  `infra/database/production_roles.sql`.
- Variáveis sensíveis fornecidas pelo cofre ou pelo mecanismo seguro da
  plataforma ao processo do Docker Compose.

## Entradas obrigatórias

Aplicação e infraestrutura:

- `LOADX_DOMAIN`: domínio sem protocolo, como `loadx.example.com`.
- `LOADX_APP_DATABASE_URL`: URL do papel restrito da aplicação.
- `LOADX_MIGRATION_DATABASE_URL`: URL do papel autorizado a executar Alembic.
- `LOADX_SECRET_KEY`: segredo aleatório exclusivo com pelo menos 32 caracteres.

Discord bot:

- `DISCORD_TASKS_CHANNEL_ID`;
- `DISCORD_STATUS_CHANNEL_ID`;
- `DISCORD_GUILD_ID`;
- `DISCORD_OWNER_USER_ID`;
- `DISCORD_RENNAN_USER_ID`;
- `DISCORD_JOAO_USER_ID`;
- `DISCORD_MARLON_USER_ID`;
- `DISCORD_MARCELO_USER_ID`;
- `DISCORD_BOT_TOKEN`;
- `GITHUB_TOKEN`.

Os IDs acima não devem ser substituídos por valores reais na documentação.

`DISCORD_BOT_TOKEN` e `GITHUB_TOKEN` entram no container do bot como secrets do
Compose. As URLs de banco e `LOADX_SECRET_KEY` também são tratadas como secrets
pela referência de produção.

`LOADX_PASSWORD_BLOCKLIST_FILE` pode apontar para uma lista UTF-8 aprovada. O
arquivo de exemplo existe apenas para validar a configuração e não substitui a
curadoria operacional. `BACKEND_WORKERS` usa `2` por padrão.

A lista completa e o fluxo entre ambientes estão em
`docs/13-guia-execucao-ambientes.md`.

## Validação e inicialização

```bash
docker compose -f compose.production.yaml config --quiet
docker compose -f compose.production.yaml up -d --build --wait
```

`CONFIRMADO`: somente Caddy publica portas. Ele termina TLS, serve o build
estático, encaminha `/api/*`, `/health` e `/ready` e ignora valores
`X-Forwarded-*` enviados diretamente pelo cliente. O Uvicorn aceita esses
headers somente do IP fixo `172.30.0.10` do Caddy.

`CONFIRMADO`: as URLs do banco e `SECRET_KEY` entram nos containers como arquivos
em `/run/secrets`, e não como variáveis de ambiente dos serviços. Migration e
aplicação recebem URLs distintas.

`RISCO IDENTIFICADO`: o Compose é uma referência de nó único. Backup, alta
disponibilidade, firewall, observabilidade, rotação do cofre e restauração
continuam responsabilidades da plataforma escolhida.

## Alertas

O backend escreve eventos JSON no logger `loadx.security`. O coletor escolhido
deve preservar `event`, `occurred_at` e `alert` e abrir alerta quando
`alert=true`. Isso cobre tentativas contra contas privilegiadas, bloqueios de
login e alterações de papel/desativação; o destino e o SLA ainda dependem da
plataforma de observabilidade.

## Sinais operacionais — OC77

`CONFIRMADO`: aplicação emite JSON em stdout nos loggers `loadx.operations` e
`loadx.security`. Use `docker compose -f compose.production.yaml logs backend`
para diagnóstico local no host. Agregue todos os workers e instâncias; cada
worker emite seus próprios eventos. Não há envio externo configurado.

| Evento | Contexto seguro / uso |
|---|---|
| `APP_STARTED`, `APP_STOPPED` | Ciclo de vida por processo; início não comprova banco saudável |
| `HTTP_REQUEST_COMPLETED` | `request_id`, `method`, template `route`, `status_code`, `duration_ms`; tráfego, latência e taxa de erros |
| `HTTP_REQUEST_FAILED` | `request_id`, template `route`, `exception_type`, status 500; erro inesperado |
| `READINESS_FAILED` | `request_id`, `reason` controlado; PostgreSQL indisponível, orçamento excedido ou Alembic divergente |
| `NOTIFICATION_FAILED` | `reason` controlado, `exception_type`; preparação/envio de aviso falhou sem desfazer operação |

`CONFIRMADO`: campos comuns são `occurred_at` UTC, `service`, `level`, `event`,
`alert` e `request_id` (nulo fora de requisição). Erros 5xx, readiness e falhas de
notificação marcam `alert=true`. Eventos de segurança mantêm seu contrato.

`CONFIRMADO`: `OPERATIONAL_LOG_LEVEL=INFO|WARNING|ERROR` limita eventos operacionais;
padrão `INFO`. `OPERATIONAL_REQUEST_LOGS=true|false` controla eventos de término
HTTP; padrão `true`. Correlação `X-Request-ID`, erros críticos e sondas continuam
ativos com os logs de término desativados (sujeitos ao nível escolhido). O nível
de segurança continua `INFO`. Valores inválidos impedem inicialização.

`CONFIRMADO`: `X-Request-ID` é UUID novo por requisição, não reflete valores do
cliente. Logs usam templates de rota, nunca valores dos parâmetros ou query
strings; caminhos desconhecidos viram `__unmatched__`. Mensagens de exceção e
tracebacks não são emitidos. Ao executar Uvicorn manualmente, inclua
`--no-access-log` como nos Dockerfiles/Compose para evitar o log HTTP nativo.
Caddy filtra URI, headers de entrada/saída, host, IP/porta e dados TLS nos logs
de acesso; status, duração e tamanho permanecem disponíveis.

`RECOMENDAÇÃO`: o coletor pode contar 5xx por template/status, agregar latência
por `duration_ms`, detectar falhas de notificação/readiness e correlacionar por
`request_id`. Nunca agregue por UUID de requisição como label de métrica.
`PENDENTE DE DEFINIÇÃO`: coletor, destino, retenção, limiares, SLA e destinatários
exigem decisão da equipe. `alert=true` não envia alerta por si só. Não há endpoint
público `/metrics`, fornecedor pago, dashboard de negócio ou armazenamento novo.

### Diagnóstico e verificações

1. `/health` verifica processo; `/ready` verifica PostgreSQL 16 e head Alembic,
   somente leitura e orçamento de 2 segundos. Não substituir readiness por health.
2. Em `READINESS_FAILED`, consultar `reason`; validar conectividade/credenciais
   no mecanismo seguro e migrations no serviço `migrate`, sem copiar valores aos logs.
3. Em 500, localizar `HTTP_REQUEST_FAILED` pelo `X-Request-ID`, template da rota
   e tipo de exceção. Reproduzir no desenvolvimento com dados fictícios.
4. Em `NOTIFICATION_FAILED`, verificar provider/transporte; a operação de negócio
   já confirmada não deve ser repetida apenas para reenviar aviso.
5. Para falha de inicialização antes de a aplicação importar, verificar estado,
   código de saída e configuração segura do container; eventos da aplicação não
   substituem monitoramento do runtime nem alertas de ausência de sinais.

`CONFIRMADO`: testes em `backend/tests/unit/test_observability.py`, sondas em
`backend/tests/test_health.py` e integração em `backend/tests/integration/test_readiness.py`.
ADR proposta: `docs/decisions/ADR-025-observabilidade-operacional.md`.
