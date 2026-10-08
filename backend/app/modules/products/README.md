# Produtos

Dimensões, peso, fragilidade, empilhamento e permissão de rotação. Quantidade pertence ao pedido.

## Estrutura

- `models.py`: entidade SQLAlchemy `Product`.
- `schemas.py`: contratos Pydantic `ProductCreate`, `ProductUpdate` e `ProductRead`.
- `repository.py`: consultas e persistência de produtos.
- `service.py`: regras de código único, criação, consulta e atualização.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `GET /api/v1/products`: lista produtos no envelope paginado da ADR-017.
- `POST /api/v1/products`: cria produto.
- `GET /api/v1/products/{id}`: consulta produto por ID.
- `PATCH /api/v1/products/{id}`: atualiza campos enviados.

`CONFIRMADO`: `ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` podem consultar. Somente
`LOGISTICS_MANAGER` pode criar ou atualizar. `DRIVER` não acessa os endpoints do
módulo na API atual.

## Regras implementadas

- Código é normalizado para maiúsculas.
- Código deve ser único.
- Dimensões e peso devem ser maiores que zero.
- `weight_kg` permanece `Decimal` internamente e usa exclusivamente número JSON
  na entrada e na saída, conforme D06 e ADR-016.
- Quantidade não pertence ao cadastro de produto; ela será informada no item do pedido.
- Fragilidade, empilhamento e permissão de rotação ficam no cadastro para uso posterior no planejamento.
- Todas as rotas exigem sessão em cookie e consultam o papel e o estado atual do usuário no banco.

## OC105 — arquivamento lógico

`CONFIRMADO`: `active=false` significa arquivado, sem DELETE e sem remoção de
referências históricas. PATCH com `active=true` reativa, validando o cadastro
completo e mantendo as unicidades globais. Só LOGISTICS_MANAGER escreve.
Alterações de estado registram ator, entidade e campo `active` na auditoria,
na mesma transação; repetições não criam eventos duplicados.

`CONFIRMADO`: a coleção usa `archive_status=active|archived|all`, default
`active`, filtrado no PostgreSQL antes da paginação. Consulta por ID não esconde
arquivados. Os contratos de disponibilidade mantêm a visão de cadastro e
conflito separados; operações existentes preservam histórico e RBAC.
