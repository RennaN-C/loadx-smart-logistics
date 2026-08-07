# Testes do backend

- `unit`: regras puras, services e otimizador, sem banco externo. Os poucos
  testes unitários de persistência usam SQLite isolado e nunca substituem a
  validação oficial das migrations.
- `integration`: API, repositories e PostgreSQL 16 exclusivo de teste, criado
  pelas migrations Alembic.
- `e2e`: fluxo completo quando o MVP estiver integrado.

`CONFIRMADO`: readiness possui testes unitários de orçamento, sigilo e
comparação de revisions, além de integração real com PostgreSQL disponível,
indisponível e fora do Alembic head.

## Comandos

Testes unitários, sem PostgreSQL:

```powershell
python -m pytest -q tests/unit tests/test_health.py
```

Testes de integração:

```powershell
docker compose -p loadx-tests -f compose.test.yaml up -d --wait
$env:TEST_DATABASE_URL = "postgresql+psycopg://loadx_test:loadx_test_local@127.0.0.1:55432/loadx_test"
Set-Location backend
python -m pytest -q tests/integration
Set-Location ..
docker compose -p loadx-tests -f compose.test.yaml down -v
```

Os comandos Docker são executados na raiz. O `pytest` é executado na pasta
`backend`. A fixture recusa banco diferente de `loadx_test`, recusa a mesma URL
da aplicação e exige PostgreSQL 16.

Cenários mínimos do otimizador:

- todos os volumes cabem;
- item excede dimensões;
- peso excede limite;
- rotação bloqueada;
- colisão proibida;
- item não empilhável;
- resultado reproduzível.
