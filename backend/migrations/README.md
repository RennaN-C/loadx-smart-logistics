# Migrations

O Alembic versiona toda alteração estrutural do PostgreSQL.

## Arquivos oficiais

- `alembic.ini`: configuração principal do Alembic.
- `migrations/env.py`: carrega `settings.database_url` e `Base.metadata`.
- `migrations/script.py.mako`: template das revisions.
- `migrations/versions`: migrations versionadas.

`CONFIRMADO`: o head atual é `20260804_0004`, que cria `load_plans`,
`load_plan_orders` e `load_plan_items` com snapshots e FKs restritivas.

## Comandos

Execute a partir da pasta `backend`:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic downgrade -1
```

Com Docker Compose, a partir da raiz:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
```

`CONFIRMADO`: `docker compose up` executa automaticamente `alembic upgrade
head` no serviço one-shot `migrate`. O backend só inicia se esse serviço terminar
com sucesso; `/ready` apenas confere o resultado e não altera o banco.

## Regras

- Nunca envie somente um SQL solto.
- Nunca altere o staging manualmente como solução definitiva.
- A migration deve subir junto com models, testes e atualização do modelo de dados.
- Revise `upgrade()` e `downgrade()` antes de abrir PR.
- Use dados fictícios em seeds e testes.
