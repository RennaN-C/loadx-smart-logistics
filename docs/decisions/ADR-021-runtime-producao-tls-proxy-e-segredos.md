# ADR-021: runtime de produção com TLS, proxy confiável e segredos montados

Status: aceita

## Contexto

A `ADR-019` definiu o Compose existente como ambiente local. Depois da OC60, a
sessão por cookie seguro exige HTTPS real, a limitação por IP precisa distinguir
o cliente sem confiar em headers forjados e migration e aplicação não devem
compartilhar um papel PostgreSQL com permissão estrutural.

`CONFIRMADO`: nesta etapa o LoadX continua atendendo somente o frontend próprio.
Domínio, provedor de nuvem, cofre e PostgreSQL gerenciado ainda não foram
escolhidos.

## Decisão

- A OC61 adiciona `compose.production.yaml` como referência separada do Compose
  local; nenhum segredo ou domínio real é versionado.
- Caddy serve o build estático e é o único serviço publicado. Ele obtém TLS,
  redireciona HTTP para HTTPS e encaminha `/api/*`, `/health` e `/ready` ao
  backend na rede privada.
- Frontend e API usam a mesma origem. O build recebe `VITE_API_URL=/api/v1` e o
  CORS aceita somente `https://<LOADX_DOMAIN>`.
- O Caddy ocupa o IP privado fixo `172.30.0.10`. Uvicorn processa
  `X-Forwarded-For` e `X-Forwarded-Proto` somente quando a conexão imediata vem
  desse IP; `*` não é usado como proxy confiável.
- `SECRET_KEY` e as URLs do PostgreSQL entram nos containers como arquivos em
  `/run/secrets`. O mecanismo que fornece os valores ao Compose pode ser um
  cofre da plataforma.
- O serviço `migrate` recebe `LOADX_MIGRATION_DATABASE_URL`; o backend recebe
  `LOADX_APP_DATABASE_URL`. O papel `loadx_app` possui somente DML e uso de
  schema/sequências; `loadx_migrator` cria e altera a estrutura via Alembic sem
  ser superusuário, `CREATEDB` ou `CREATEROLE`.
- PostgreSQL de produção é externo ao Compose de referência. Backup,
  restauração, criptografia de volume e alta disponibilidade pertencem à
  plataforma escolhida.

## Consequências

- O cookie `__Host-loadx_session` pode operar sob HTTPS e os headers do cliente
  chegam ao backend por uma fronteira de proxy explícita.
- A aplicação comprometida não recebe permissão para criar ou remover tabelas.
- A mesma imagem do backend aceita segredos de ambiente local ou arquivos
  montados; variáveis de ambiente têm precedência intencional.
- `RISCO IDENTIFICADO`: Caddy automático depende de DNS e portas públicas 80/443.
- `RISCO IDENTIFICADO`: o Compose continua sendo referência de nó único e não é
  evidência de prontidão operacional sem backup restaurado, monitoramento,
  rotação e teste no domínio real.
- `PENDENTE DE DEFINIÇÃO`: o provedor final de cofre, PostgreSQL, logs e alertas
  será escolhido junto da plataforma de produção.

## Referências

- [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
- [Docker Compose secrets](https://docs.docker.com/reference/compose-file/secrets/).
- [Uvicorn proxy headers](https://www.uvicorn.org/settings/).
- [PostgreSQL ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html).
