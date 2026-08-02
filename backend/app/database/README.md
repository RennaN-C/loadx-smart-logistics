# Database

Conexão SQLAlchemy, sessão, base declarativa e utilidades de persistência.

## Regras

- alterações estruturais por Alembic;
- não criar tabelas automaticamente em produção;
- repositories recebem uma sessão;
- `integrity.py` lê o nome de constraints reportado pelo PostgreSQL/psycopg para permitir mapeamento seguro de erros conhecidos;
- não guardar regra de negócio nesta pasta.
