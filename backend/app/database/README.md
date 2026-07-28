# Database

Conexão SQLAlchemy, sessão, base declarativa e utilidades de persistência.

## Regras

- alterações estruturais por Alembic;
- não criar tabelas automaticamente em produção;
- repositories recebem uma sessão;
- não guardar regra de negócio nesta pasta.
