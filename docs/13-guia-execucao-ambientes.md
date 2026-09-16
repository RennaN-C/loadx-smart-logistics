# Guia de execução e ambientes

Este documento é a referência central para configurar, executar, testar e
validar o LoadX nos ambientes atualmente suportados pelo repositório.

Ele não substitui:

- `CONTRIBUTING.md`, para fluxo de contribuição;
- `SECURITY.md`, para reporte responsável;
- `docs/08-padroes-desenvolvimento.md`, para padrões técnicos;
- `backend/tests/README.md`, para detalhes dos testes do backend;
- `infra/production/README.md`, para a referência de produção.

## Ambientes suportados

O repositório confirma três contextos distintos:

1. **local**: desenvolvimento com `compose.yaml`;
2. **teste/CI**: validação automatizada com PostgreSQL exclusivo de teste;
3. **produção de referência**: nó único com `compose.production.yaml`.

Não trate esses ambientes como equivalentes. Banco, segredos, exposição de
portas e objetivo operacional são diferentes.

## Versões técnicas confirmadas

As versões abaixo são definidas pelos arquivos executáveis atuais:

- Python: `3.12`;
- Node.js: `22.23.1`, definido em `frontend/.nvmrc`;
- PostgreSQL: `16`;
- frontend: instalado a partir de `frontend/package-lock.json`;
- backend: instalado a partir dos locks versionados em `backend/`.

Ao atualizar essas versões no código ou na CI, atualize também este guia.

## Ambiente local

### Pré-requisitos

Instale Git e Docker com Docker Compose.

Python 3.12 e Node.js compatível com `frontend/.nvmrc` só são necessários para
executar backend ou frontend diretamente fora dos containers.

### Preparar o `.env`

No PowerShell:

    Copy-Item .env.example .env

Em Bash:

    cp .env.example .env

Preencha no mínimo `POSTGRES_PASSWORD`.

O Compose local exige essa senha. Use uma senha exclusiva para desenvolvimento
e nunca versione `.env`.

### Validar a configuração

    docker compose config --quiet

O comando deve terminar sem erro.

### Subir o ambiente

    docker compose up --build

Em segundo plano:

    docker compose up -d --build

A ordem operacional é:

    db saudável
        |
    migrate executa alembic upgrade head
        |
    backend inicia e expõe readiness
        |
    frontend inicia

O `compose.yaml` publica as portas somente em loopback por padrão.

### Verificar o ambiente

Com os serviços ativos:

    Frontend:              http://localhost:5173
    Backend:               http://localhost:8000
    Documentação da API:   http://localhost:8000/docs
    Liveness:              http://localhost:8000/health
    Readiness:             http://localhost:8000/ready

`/docs` existe no ambiente local.

`/health` indica que o processo está em execução.

`/ready` só retorna sucesso quando PostgreSQL está acessível e o banco está na
revisão Alembic esperada.

### Serviços do Compose local

`db` executa PostgreSQL 16 e persiste dados no volume `postgres_data`.

`migrate` é um serviço one-shot responsável por `python -m alembic upgrade head`.
O backend só inicia depois que ele termina com sucesso.

`backend` executa FastAPI/Uvicorn em modo de desenvolvimento com reload e usa a
porta `8000` por padrão.

`frontend` executa Vite em modo de desenvolvimento, usa a porta `5173` por
padrão e encaminha chamadas de API para o backend.

### Encerrar o ambiente

    docker compose down

Esse comando preserva o volume local do PostgreSQL.

Para remover também o volume:

    docker compose down -v

**Atenção:** `down -v` remove os dados armazenados no banco local desse Compose.
Use somente quando essa perda de dados for intencional.

## Ambiente de testes

Testes de integração usam um PostgreSQL separado do desenvolvimento.

`compose.test.yaml` publica por padrão o PostgreSQL de teste em
`127.0.0.1:55432` e usa o banco `loadx_test`.

Nunca aponte `TEST_DATABASE_URL` para desenvolvimento, staging ou produção.

No PowerShell:

    docker compose -p loadx-tests -f compose.test.yaml up -d --wait
    $env:TEST_DATABASE_URL = "postgresql+psycopg://loadx_test:loadx_test_local@127.0.0.1:55432/loadx_test"

Depois execute os testes conforme `backend/tests/README.md`.

Ao terminar:

    docker compose -p loadx-tests -f compose.test.yaml down -v

Nesse fluxo o banco é exclusivo de teste e descartável.

## Validações locais equivalentes à CI

A CI é a validação final. Para reproduzir localmente os checks principais, use
as mesmas versões de runtime.

### Backend

Na pasta `backend`:

    python -m pip install --require-hashes -r requirements-dev.lock.txt
    python -m ruff check .
    python -m ruff format --check .
    python -m alembic upgrade head
    python -m pytest -q tests --cov=app --cov-report=term

Os testes que usam banco exigem PostgreSQL 16 exclusivo e `TEST_DATABASE_URL`
válida. Consulte `backend/tests/README.md`.

### Frontend

Na pasta `frontend`:

    npm ci --ignore-scripts
    npm audit --audit-level=high
    npm run lint
    npm test -- --run
    npm run build

Use a versão indicada em `frontend/.nvmrc`.

### Segurança do backend

A CI também constrói `backend/Dockerfile` e verifica vulnerabilidades HIGH e
CRITICAL da imagem com Trivy, ignorando apenas vulnerabilidades ainda sem
correção disponível.

A reprodução exata permanece definida em `.github/workflows/ci.yml`.

## Produção de referência

`compose.production.yaml` é uma referência de produção de nó único.

Ele não representa deploy específico de AWS, Azure, WispByte ou outro provedor.

A topologia confirmada é:

    Internet
       |
    Caddy / frontend
    80 e 443
       |
    rede privada Docker
       |
    backend
       |
    PostgreSQL externo ou privado

O serviço `migrate` executa migrations antes do backend.

O backend não publica porta diretamente no host.

### Entradas obrigatórias

Aplicação e infraestrutura:

- `LOADX_DOMAIN`;
- `LOADX_APP_DATABASE_URL`;
- `LOADX_MIGRATION_DATABASE_URL`;
- `LOADX_SECRET_KEY`.

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

Entradas opcionais incluem:

- `LOADX_PASSWORD_BLOCKLIST_FILE`;
- `BACKEND_WORKERS`.

Não coloque valores reais na documentação ou no repositório.

### Validar a configuração de produção

    docker compose -f compose.production.yaml config --quiet

### Subir a referência de produção

    docker compose -f compose.production.yaml up -d --build --wait

Leia `infra/production/README.md` antes de executar.

A plataforma real continua responsável por backup, restauração, firewall,
observabilidade, rotação de segredos e disponibilidade.

## Troubleshooting

### `.env` não encontrado

Se aparecer erro como `env file .../.env not found`, crie `.env` a partir de
`.env.example` e preencha as variáveis locais necessárias.

### `POSTGRES_PASSWORD` não definido

Se `docker compose config` reclamar de `POSTGRES_PASSWORD`, preencha a senha no
`.env`. Não coloque a senha em `.env.example`.

### Porta já está em uso

No `.env` local podem ser alteradas:

- `POSTGRES_PORT`;
- `BACKEND_PORT`;
- `FRONTEND_PORT`.

Para testes, use `TEST_POSTGRES_PORT`.

Depois valide novamente com `docker compose config --quiet`.

### Migration falhou

Verifique:

    docker compose ps
    docker compose logs migrate
    docker compose logs db

Não force o backend ignorando o serviço `migrate`.

### `/ready` retorna falha

Verifique:

    docker compose ps
    docker compose logs backend
    docker compose logs migrate
    docker compose logs db

Readiness depende de PostgreSQL acessível e Alembic no head.

### Preciso recriar o banco local

Antes de executar `docker compose down -v`, confirme que os dados locais podem
ser descartados. Esse comando remove o volume e causa perda dos dados armazenados
no banco local.

## Fonte de verdade

Quando houver divergência entre este guia e arquivos executáveis, prevalecem:

- `compose.yaml`;
- `compose.test.yaml`;
- `compose.production.yaml`;
- `.github/workflows/ci.yml`;
- `backend/Dockerfile`;
- `frontend/.nvmrc`;
- locks de dependências.

A divergência deve ser corrigida na documentação pelo fluxo normal de Issue e
Pull Request.
