# Banco e seeds

Scripts de seed, backup de demonstração e instruções do ambiente staging.

Não coloque dump com dados reais. A estrutura oficial vem das migrations do backend.

`CONFIRMADO`: `docker compose up` preserva o volume nomeado `postgres_data`,
espera o PostgreSQL 16 ficar saudável e executa `alembic upgrade head` no
serviço one-shot `migrate` antes de liberar o backend. A porta do banco fica
restrita a `127.0.0.1` por padrão.
