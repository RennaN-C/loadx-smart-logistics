# Testes de integração

`CONFIRMADO`: esta suíte usa exclusivamente PostgreSQL 16 e aplica a cadeia real
de migrations com `alembic upgrade head`. Não use SQLite,
`Base.metadata.create_all`, banco de desenvolvimento, staging ou produção.

## Banco exclusivo

O serviço `db-test` fica em `compose.test.yaml`, usa o banco `loadx_test`, não
compartilha o volume de desenvolvimento e publica somente a porta local `55432`.

Antes da suíte, a fixture:

1. valida driver, nome do banco e versão PostgreSQL;
2. recria somente o schema `public` do banco exclusivo;
3. executa `alembic upgrade head` do banco vazio;
4. exercita `alembic downgrade -1`;
5. reaplica `alembic upgrade head`;
6. isola cada teste em transação externa com savepoints.

Execute a partir da raiz e depois de `backend`:

```powershell
docker compose -p loadx-tests -f compose.test.yaml up -d --wait
Set-Location backend
$env:TEST_DATABASE_URL = "postgresql+psycopg://loadx_test:loadx_test_local@127.0.0.1:55432/loadx_test"
python -m pytest -q tests/integration
```

Ao terminar, a partir da raiz:

```powershell
docker compose -p loadx-tests -f compose.test.yaml down -v
```

As credenciais acima são exclusivamente locais e fictícias. Uma URL ausente ou
insegura encerra a suíte antes de qualquer reset de schema.

`CONFIRMADO`: `test_authorization_matrix.py` cruza todas as operações protegidas
com `ADMIN`, `LOGISTICS_MANAGER`, `CHECKER` e `DRIVER`. `test_openapi.py` garante
que somente `/health`, `/ready` e `/api/v1/auth/login` permaneçam públicos no
contrato atual.

`CONFIRMADO`: `test_readiness.py` valida sucesso no PostgreSQL migrado, falha
genérica com banco indisponível e rejeição de revisão diferente do head.

`CONFIRMADO`: `test_postgresql_migrations.py` verifica PostgreSQL 16, revision
Alembic, tabelas oficiais, FK, `CHECK`, UUID, `Numeric` e timestamp com timezone.
