# Instruções de IA para o backend

Além do `AGENTS.md` da raiz:

- use Python 3.12 e type hints;
- use SQLAlchemy 2 com estilo assíncrono apenas se o projeto adotar isso integralmente;
- nesta base, o padrão inicial é sessão síncrona para reduzir complexidade acadêmica;
- valide entradas com Pydantic;
- mantenha serviços independentes de FastAPI quando possível;
- escreva testes unitários para regras e testes de integração para rotas;
- não crie modelos ou migrations sem atualizar `docs/03-modelo-dados.md`.
- siga os padrões de camadas, nomes, erros, logs e testes em `docs/08-padroes-desenvolvimento.md`;
- consulte `docs/09-guia-para-ia.md` antes de criar arquivos novos.
