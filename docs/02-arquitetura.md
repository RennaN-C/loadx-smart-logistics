# Arquitetura

## Estilo

Monólito modular com frontend separado consumindo API REST.

```text
React + TypeScript
        |
        | HTTP/JSON
        v
FastAPI modular
        |
        | SQLAlchemy
        v
PostgreSQL
```

## Backend

Cada módulo possui responsabilidade própria. Rotas chamam serviços; serviços aplicam regras; repositórios acessam o banco.

```text
router -> schema -> service -> repository -> model
                       |
                       -> domain/optimizer
```

## Frontend

Organização por funcionalidades. Cada feature possui páginas, componentes, hooks, tipos e chamadas de API relacionadas.

## Integrações

IA e WhatsApp são adaptadores substituíveis. O desenvolvimento começa com providers mock para não bloquear o restante do sistema.

## Dependências permitidas

- Módulos podem consumir serviços públicos de outros módulos.
- O módulo de planejamento pode consultar caminhões, produtos e pedidos.
- A visualização 3D consome somente o resultado aprovado do planejamento.
- Integrações externas não acessam o banco diretamente.

## Dependências proibidas

- Frontend calculando validade geométrica.
- IA decidindo se uma solução física é válida.
- Rotas HTTP contendo regras complexas.
- Um módulo alterando diretamente modelos internos de outro módulo.
