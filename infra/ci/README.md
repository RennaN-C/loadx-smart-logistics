# Integração contínua

`CONFIRMADO`: a integração contínua do LoadX está implementada em
`.github/workflows/ci.yml`. O workflow executa em pull requests destinados a
`desenvolvimento` e `main` e em pushes para essas duas branches, sem filtro por
caminho. Execuções anteriores do mesmo pull request são canceladas quando um
novo commit é enviado.

## Backend

O job independente `Backend` usa Ubuntu, Python 3.12 e um serviço PostgreSQL 16
com o banco exclusivo `loadx_test`. A sequência validada é:

1. instalar as dependências travadas de `backend/requirements.lock.txt` com
   `python -m pip install --require-hashes`;
2. executar `python -m ruff check .`;
3. executar `python -m ruff format --check .`;
4. aplicar `python -m alembic upgrade head`;
5. executar a suíte completa com Pytest e relatório de cobertura.

`CONFIRMADO`: `backend/requirements.txt` permanece como declaração das
dependências diretas e seus intervalos aceitos. O arquivo
`backend/requirements.lock.txt`, gerado em Python 3.12, fixa as versões diretas
e transitivas e registra hashes SHA-256. A CI instala exclusivamente o lock com
`--require-hashes`, sem atualizar o `pip` de forma não versionada.

## Frontend

O job independente `Frontend` usa Ubuntu e a versão de Node definida em
`frontend/.nvmrc`. A sequência validada é:

1. instalar o `package-lock.json` com `npm ci --ignore-scripts`;
2. executar ESLint com `npm run lint`;
3. executar Vitest com `npm test -- --run`;
4. executar o build de produção e o orçamento do bundle com `npm run build`.

## Proteção de integração

`CONFIRMADO`: o PR #23 passou integralmente pelos checks `Backend`, `Frontend`
e `SonarCloud`.

`CONFIRMADO`: `main` possui ruleset ativo que exige os checks `Backend`,
`Frontend` e `SonarCloud`, além de pelo menos uma aprovação, antes do merge.
Falha ou ausência de qualquer requisito mantém a integração bloqueada.
