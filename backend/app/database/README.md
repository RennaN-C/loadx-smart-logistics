# Database

Conexão SQLAlchemy, sessão, base declarativa e utilidades de persistência.

## Regras

- alterações estruturais por Alembic;
- não criar tabelas automaticamente em produção;
- repositories recebem uma sessão;
- `integrity.py` lê o nome de constraints reportado pelo PostgreSQL/psycopg para permitir mapeamento seguro de erros conhecidos;
- `readiness.py` executa `SELECT 1` e compara `alembic_version` com os heads
  entregues, usando conexão somente leitura e timeout limitado;
- não guardar regra de negócio nesta pasta.

`CONFIRMADO`: a verificação de readiness nunca aplica migrations e não propaga
URL, credencial, revisão ou mensagem bruta do driver para a resposta pública ou
para logs.

`CONFIRMADO`: a aplicação das migrations no ambiente local é responsabilidade
do serviço isolado `migrate` do Compose, executado antes do backend conforme
`ADR-019`.
