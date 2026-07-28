# ADR-001: monólito modular

Status: aceita

## Contexto

O grupo possui quatro desenvolvedores e precisa entregar um MVP acadêmico integrado.

## Decisão

Usar uma única API FastAPI organizada por módulos internos, um frontend React e um PostgreSQL.

## Consequências

Menos infraestrutura e deploys. Os limites entre módulos devem ser mantidos por organização e revisão de código.
