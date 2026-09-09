# Banco e seeds

Scripts de seed, backup de demonstração e instruções do ambiente staging.

Não coloque dump com dados reais. A estrutura oficial vem das migrations do backend.

`CONFIRMADO`: `docker compose up` preserva o volume nomeado `postgres_data`,
espera o PostgreSQL 16 ficar saudável e executa `alembic upgrade head` no
serviço one-shot `migrate` antes de liberar o backend. A porta do banco fica
restrita a `127.0.0.1` por padrão.

## Papéis de produção

`production_roles.sql` deve ser executado por um administrador no banco vazio,
antes da primeira migration:

```bash
psql "$ADMIN_DATABASE_URL" -f infra/database/production_roles.sql
```

Depois, ainda na sessão administrativa, use `\password loadx_migrator` e
`\password loadx_app` para cadastrar valores vindos do cofre sem colocá-los no
histórico SQL ou na linha de comando. Automação deve usar o mecanismo
parametrizado e protegido oferecido pelo PostgreSQL gerenciado escolhido.

`CONFIRMADO`: `loadx_migrator` pode criar estruturas no schema `public` e
concede DML por privilégios padrão. `loadx_app` recebe somente uso do schema,
DML nas tabelas e uso das sequências; não recebe `CREATE`, superusuário,
`CREATEDB` ou `CREATEROLE`.

`RISCO IDENTIFICADO`: o script é preparado para a primeira implantação. Em um
banco já existente com objetos de outro proprietário, a transferência de
ownership exige plano e backup específicos.
