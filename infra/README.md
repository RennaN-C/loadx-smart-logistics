# Infraestrutura

Arquivos auxiliares de ambiente local, banco, scripts e CI.

O `compose.yaml` principal fica na raiz para simplificar a execução. Esta pasta guarda documentação e arquivos complementares.

- `production/`: pré-requisitos e entradas do `compose.production.yaml`.
- `database/production_roles.sql`: separação entre migration e aplicação.

`CONFIRMADO`: o Compose principal continua exclusivo do desenvolvimento local.
O arquivo de produção segue `ADR-021` e não inclui PostgreSQL, domínio ou
credenciais reais.
