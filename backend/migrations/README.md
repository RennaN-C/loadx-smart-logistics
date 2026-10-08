# Migrations

O Alembic versiona toda alteração estrutural do PostgreSQL.

## Arquivos oficiais

- `alembic.ini`: configuração principal do Alembic.
- `migrations/env.py`: carrega `settings.database_url` e `Base.metadata`.
- `migrations/script.py.mako`: template das revisions.
- `migrations/versions`: migrations versionadas.

`CONFIRMADO`: o head atual é `20261008_0016` (OC105), após OC87
`20261007_0015` e evidências OC80 `20261007_0014`. A OC87 cria necessidade/partes/claims e triggers de integridade
diferidas; downgrade remove esses registros/triggers e tipos de histórico próprios.
A revisão `20260830_0011` adiciona
`trips.created_at` para ordenação determinística e sucede as migrations de
ocorrências e carregamento. `20260809_0007` vincula usuários a motoristas;
`20260809_0008` fecha o catálogo auditável e cria `trips` e `deliveries`. As
revisões anteriores da OC60 criam `auth_login_throttles`, sem e-mail ou IP
brutos, e `auth_sessions`, que persiste somente o hash do identificador opaco.

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

`CONFIRMADO` (OC105): head `20261008_0016` → down_revision `20261007_0015`.
Adiciona `active` com default true a clientes/produtos e expande o catálogo
restrito de auditoria. Upgrade preserva UUIDs, documentos, códigos e todas as
FKs. Downgrade **não** apaga eventos de auditoria nem reativa cadastros
silenciosamente: é bloqueado se houver clientes/produtos arquivados ou qualquer
evento específico de ciclo de vida da OC105. Somente é permitido quando não
existe estado ou auditoria OC105 a preservar. Para reverter após uso real,
planeje migração compensatória com preservação de dados; não remova registros
de auditoria para forçar o downgrade.
