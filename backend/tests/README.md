# Testes do backend

- `unit`: regras puras e otimizador, sem banco externo.
- `integration`: API, repositories e PostgreSQL de teste.
- `e2e`: fluxo completo quando o MVP estiver integrado.

Cenários mínimos do otimizador:

- todos os volumes cabem;
- item excede dimensões;
- peso excede limite;
- rotação bloqueada;
- colisão proibida;
- item não empilhável;
- resultado reproduzível.
