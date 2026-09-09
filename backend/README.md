# Backend

API FastAPI do LoadX.

## Organização

- `app/core`: configurações e segurança.
- `app/database`: conexão, base e sessão.
- `app/api`: agregação de rotas.
- `app/modules`: módulos de negócio.
- `app/integrations`: IA e WhatsApp por adaptadores.
- `app/shared`: tipos e utilitários realmente compartilhados.
- `migrations`: alterações versionadas do banco.
- `tests`: testes unitários e integrados.

## Regra de camadas

```text
router -> service -> repository -> database
              |
              -> domain/optimizer
```

Não coloque regras de negócio em `router.py` nem SQL direto nos serviços.

## Primeiro administrador

Depois de aplicar as migrations e antes de expor a API, crie o primeiro administrador com o comando interativo:

```bash
python -m app.modules.auth.bootstrap
```

Com Docker Compose, execute a partir da raiz sem publicar a porta do backend:

```bash
docker compose run --rm backend python -m app.modules.auth.bootstrap
```

A senha é solicitada de forma oculta e não deve ser informada em argumento, `.env`, seed ou log. O comando recusa nova execução quando o banco já possui qualquer usuário.

## Sondas operacionais

- `GET /health`: liveness; confirma apenas que o processo HTTP está ativo.
- `GET /ready`: readiness; exige PostgreSQL acessível e Alembic exatamente no
  head.

`CONFIRMADO`: `/ready` é público para Compose e monitoramento, executa somente
leitura, possui orçamento de 2 segundos e retorna falha genérica sem detalhes de
infraestrutura, conforme D11 e `ADR-018`.

## Configuração segura

`CONFIRMADO`: conforme `ADR-019` e `ADR-020`, produção exige `SECRET_KEY`
exclusiva com ao menos 32 caracteres e `DATABASE_URL` explícita, rejeita CORS
curinga e usa sessão opaca no cookie `__Host-loadx_session`. Os valores fracos de
`.env.example` existem somente para desenvolvimento local e não permitem iniciar
em produção.

`CONFIRMADO`: as respostas da API recebem CSP restritiva, `Cache-Control:
no-store`, proteção contra framing e MIME sniffing, política de referrer e
restrição de permissões do navegador. HSTS é emitido somente em `production`.
`RISCO IDENTIFICADO`: HTTPS deve ser terminado e validado pela infraestrutura de
produção; o navegador ignora HSTS recebido por uma conexão HTTP.

`PASSWORD_BLOCKLIST_PATH` é opcional e aponta para um arquivo UTF-8 com uma
senha completa por linha. Linhas vazias e iniciadas por `#` são ignoradas. Em
produção, monte somente uma lista aprovada e reinicie o processo para recarregá-la.

`LOADX_SECRETS_DIR` permite carregar `SECRET_KEY` e `DATABASE_URL` de arquivos
montados pelo orquestrador. O diretório configurado precisa existir; uma variável
de ambiente com o mesmo nome do campo tem precedência sobre o arquivo.

`CONFIRMADO`: no Compose, o serviço one-shot `migrate` aplica o head Alembic
antes do backend. A API e a migration executam como usuário sem privilégio, sem
capabilities Linux e sem possibilidade de elevar privilégios.
