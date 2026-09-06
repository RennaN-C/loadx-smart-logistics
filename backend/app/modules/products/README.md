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
