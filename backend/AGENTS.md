# Instruções de IA para o backend

Além do `AGENTS.md` da raiz:

- use Python 3.12 e type hints;
- use SQLAlchemy 2 com estilo assíncrono apenas se o projeto adotar isso integralmente;
- nesta base, o padrão inicial é sessão síncrona para reduzir complexidade acadêmica;
- valide entradas com Pydantic;
- mantenha serviços independentes de FastAPI quando possível;
- escreva testes unitários para regras e testes de integração para rotas;
- não crie modelos ou migrations sem atualizar `docs/03-modelo-dados.md`.
