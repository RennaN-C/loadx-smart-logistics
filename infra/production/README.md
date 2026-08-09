# Produção

Configuração de referência para publicar o frontend próprio e a API sob a mesma
origem HTTPS. Não contém domínio, credencial nem dado real.

## Pré-requisitos

- DNS de `LOADX_DOMAIN` apontando para o servidor.
- Portas TCP 80/443 e UDP 443 liberadas para o Caddy obter e renovar TLS.
- PostgreSQL 16 externo ou privado, já preparado com
  `infra/database/production_roles.sql`.
- Variáveis sensíveis fornecidas pelo cofre ou pelo mecanismo seguro da
  plataforma ao processo do Docker Compose.

## Entradas obrigatórias

- `LOADX_DOMAIN`: domínio sem protocolo, como `loadx.example.com`.
- `LOADX_APP_DATABASE_URL`: URL do papel restrito da aplicação.
- `LOADX_MIGRATION_DATABASE_URL`: URL do papel autorizado a executar Alembic.
- `LOADX_SECRET_KEY`: segredo aleatório exclusivo com pelo menos 32 caracteres.

`LOADX_PASSWORD_BLOCKLIST_FILE` pode apontar para uma lista UTF-8 aprovada. O
arquivo de exemplo existe apenas para validar a configuração e não substitui a
curadoria operacional. `BACKEND_WORKERS` usa `2` por padrão.

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
