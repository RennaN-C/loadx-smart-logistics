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

`CONFIRMADO`: conforme `ADR-019`, produção exige `SECRET_KEY` exclusiva com ao
menos 32 caracteres e `DATABASE_URL` explícita, aceita somente JWT `HS256`,
limita a expiração a 1–1440 minutos e rejeita CORS curinga. Os valores fracos de
`.env.example` existem somente para desenvolvimento local e não permitem iniciar
em produção.

`CONFIRMADO`: no Compose, o serviço one-shot `migrate` aplica o head Alembic
antes do backend. A API e a migration executam como usuário sem privilégio, sem
capabilities Linux e sem possibilidade de elevar privilégios.
