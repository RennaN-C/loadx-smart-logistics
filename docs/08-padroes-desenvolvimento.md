# Padrões de desenvolvimento

## Git

Branches:

- `main`: versão estável;
- `develop`: integração;
- `feature/OC-XX-descricao`: uma ocorrência;
- `fix/OC-XX-descricao`: correção.

Commits:

- `feat: ...`
- `fix: ...`
- `test: ...`
- `docs: ...`
- `refactor: ...`
- `chore: ...`

## Pull Request

Toda alteração entra por Pull Request para `develop`. Exigir pelo menos uma revisão.

## Banco

- cada pessoa usa PostgreSQL local;
- staging é compartilhado apenas para integração;
- alterações estruturais somente por Alembic;
- nunca editar a estrutura oficial apenas pelo pgAdmin;
- seeds devem usar dados fictícios.

## Definição de pronto

Uma ocorrência está pronta quando:

- critérios de aceite atendidos;
- código revisado;
- testes passando;
- migration incluída, quando necessária;
- documentação atualizada;
- integração verificada.

## Padrão de qualidade

- Python formatado com Ruff;
- TypeScript validado por ESLint;
- funções curtas e nomes claros;
- regras críticas com testes unitários;
- erros de API no formato documentado.
